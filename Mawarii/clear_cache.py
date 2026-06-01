# clear_cache.py
import os
import shutil

def delete_pycache():
    """حذف جميع مجلدات __pycache__ في المشروع"""
    count = 0
    for root, dirs, files in os.walk('.'):
        if '__pycache__' in dirs:
            pycache_path = os.path.join(root, '__pycache__')
            print(f'Deleting: {pycache_path}')
            shutil.rmtree(pycache_path)
            count += 1
    print(f'✅ Deleted {count} __pycache__ folders')

if __name__ == '__main__':
    delete_pycache()