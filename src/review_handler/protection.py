import json
import os
from typing import Optional

def check_protection(file_path: str) -> Optional[str]:
    """
    Проверяет, требуется ли подтверждение для изменения файла.
    
    Args:
        file_path: Путь к файлу, который планируется изменить
        
    Returns:
        str: Сообщение о необходимости подтверждения или None, если подтверждение не требуется
    """
    dir_path = os.path.dirname(file_path)
    protection_file = os.path.join(dir_path, '.protected')
    
    if not os.path.exists(protection_file):
        return None
        
    try:
        with open(protection_file, 'r') as f:
            protection_data = json.load(f)
            
        if protection_data.get('requires_confirmation'):
            file_name = os.path.basename(file_path)
            if file_name in protection_data.get('protected_files', []):
                return (
                    f"⚠️ Файл {file_name} защищен от изменений!\n"
                    f"Причина: {protection_data.get('protection_reason')}\n"
                    "Требуется подтверждение пользователя для внесения изменений."
                )
    except Exception as e:
        return f"Ошибка проверки защиты: {str(e)}"
    
    return None
