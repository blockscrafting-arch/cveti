"""
Патчи для совместимости с Python 3.14
"""
import sys

# Патч для Pydantic: исправляем проблему с prefer_fwd_module в Python 3.14
if sys.version_info >= (3, 14):
    # Импортируем typing и патчим _eval_type ДО импорта pydantic
    import typing
    
    # Сохраняем оригинальную функцию
    _original_eval_type = getattr(typing, '_eval_type', None)
    
    if _original_eval_type:
        def _patched_eval_type(value, globalns=None, localns=None, type_params=None, **kwargs):
            """Патч для _eval_type: игнорируем prefer_fwd_module в Python 3.14"""
            # Убираем prefer_fwd_module из kwargs, если он есть
            kwargs.pop('prefer_fwd_module', None)
            # Вызываем оригинальную функцию без prefer_fwd_module
            if type_params is not None:
                return _original_eval_type(value, globalns, localns, type_params, **kwargs)
            else:
                return _original_eval_type(value, globalns, localns, **kwargs)
        
        # Применяем патч
        typing._eval_type = _patched_eval_type
