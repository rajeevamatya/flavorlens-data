import psycopg2
import time
import logging
from config import get_db_connection, setup_logging

# Setup logging
setup_logging()
logger = logging.getLogger(__name__)

def batch_update_menu_items():
    """Update menu_items with image_id and date_uploaded in optimized batches"""
    
    batch_size = 50000  # Adjust based on your system performance
    total_updated = 0
    
    logger.info("Starting batch update of menu_items...")
    
    # Get total count for progress tracking
    try:
        conn = get_db_connection()
        with conn.cursor() as cursor:
            cursor.execute("""
                SELECT COUNT(*) 
                FROM menu.menu_items 
                WHERE old_image_id IS NOT NULL 
                  AND (image_id IS NULL OR date_uploaded IS NULL)
            """)
            total_rows = cursor.fetchone()[0]
            logger.info(f"Total rows to update: {total_rows:,}")
        conn.close()
    except Exception as e:
        logger.error(f"Error getting row count: {e}")
        return
    
    if total_rows == 0:
        logger.info("No rows need updating. Exiting.")
        return
    
    start_time = time.time()
    
    while True:
        try:
            conn = get_db_connection()
            with conn.cursor() as cursor:
                # Optimized batch update with DISTINCT ON to handle duplicates
                cursor.execute("""
                    WITH batch_items AS (
                        SELECT item_id, old_image_id
                        FROM menu.menu_items 
                        WHERE old_image_id IS NOT NULL 
                          AND (image_id IS NULL OR date_uploaded IS NULL)
                        LIMIT %s
                    ),
                    distinct_images AS (
                        SELECT DISTINCT ON (old_image_id) 
                               old_image_id, image_id, date_uploaded
                        FROM menu.menu_images 
                        WHERE old_image_id IN (SELECT old_image_id FROM batch_items)
                          AND old_image_id IS NOT NULL
                        ORDER BY old_image_id, image_id
                    )
                    UPDATE menu.menu_items 
                    SET image_id = di.image_id,
                        date_uploaded = di.date_uploaded
                    FROM distinct_images di
                    WHERE menu.menu_items.old_image_id = di.old_image_id
                      AND menu.menu_items.item_id IN (SELECT item_id FROM batch_items)
                """, (batch_size,))
                
                rows_updated = cursor.rowcount
                conn.commit()
                
                if rows_updated == 0:
                    logger.info("No more rows to update. Update complete!")
                    break
                
                total_updated += rows_updated
                elapsed = time.time() - start_time
                rate = total_updated / elapsed if elapsed > 0 else 0
                remaining = total_rows - total_updated
                eta = remaining / rate if rate > 0 else 0
                
                logger.info(f"Updated {rows_updated:,} rows | "
                           f"Total: {total_updated:,}/{total_rows:,} ({total_updated/total_rows*100:.1f}%) | "
                           f"Rate: {rate:.0f} rows/sec | "
                           f"ETA: {eta/60:.1f} min")
                
                # Brief pause to avoid overwhelming the database
                time.sleep(0.1)
            
            conn.close()
            
        except Exception as e:
            logger.error(f"Error during batch update: {e}")
            if 'conn' in locals():
                conn.close()
            # Wait a bit before retrying
            time.sleep(5)
            continue
    
    total_time = time.time() - start_time
    logger.info(f"\nBatch update completed successfully!")
    logger.info(f"Total rows updated: {total_updated:,}")
    logger.info(f"Total time: {total_time/60:.1f} minutes")
    logger.info(f"Average rate: {total_updated/total_time:.0f} rows/second")
    
    # Verify the results
    try:
        conn = get_db_connection()
        with conn.cursor() as cursor:
            cursor.execute("""
                SELECT 
                    COUNT(*) as total_items,
                    COUNT(image_id) as items_with_image_id,
                    COUNT(date_uploaded) as items_with_date_uploaded,
                    COUNT(CASE WHEN old_image_id IS NOT NULL AND image_id IS NULL THEN 1 END) as still_missing
                FROM menu.menu_items 
                WHERE old_image_id IS NOT NULL
            """)
            
            result = cursor.fetchone()
            logger.info(f"\nUpdate Results:")
            logger.info(f"Total items with old_image_id: {result[0]:,}")
            logger.info(f"Items with image_id: {result[1]:,}")
            logger.info(f"Items with date_uploaded: {result[2]:,}")
            logger.info(f"Items still missing data: {result[3]:,}")
        
        conn.close()
    except Exception as e:
        logger.error(f"Error verifying results: {e}")

def main():
    """Main function to run the batch update"""
    try:
        batch_update_menu_items()
    except KeyboardInterrupt:
        logger.info("Update interrupted by user. Exiting...")
    except Exception as e:
        logger.error(f"Unexpected error: {e}")

if __name__ == "__main__":
    main()