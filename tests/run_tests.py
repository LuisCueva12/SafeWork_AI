import os
import sys
import unittest

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))


def main():
    print("Iniciando pruebas de Dominio y Aplicacion (SafeWork IA)...\n")
    loader = unittest.TestLoader()
    
    # Solo descubrimos tests que no dependan fuertemente de PyQt
    # Ejecutaremos directamente nuestros tests mas criticos:
    suite = unittest.TestSuite()
    
    # Buscar dinamicamente todos los tests
    discovered_suite = loader.discover('tests', pattern='test_*.py')
    
    # Excluir explicitamente test_monitor_safework_service.py y otros que podrian estar usando UI
    for all_test_suite in discovered_suite:
        for test_case in all_test_suite:
            # unittest.discover groups tests into TestSuites
            # Iteramos en profundidad para sacar los modulos conflictivos
            if 'test_monitor_safework_service' not in str(test_case):
                suite.addTest(test_case)
            
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    
    if result.wasSuccessful():
        print("\nTodas las reglas de negocio e integraciones puras son VALIDAS.")
        sys.exit(0)
    else:
        print("\nSe encontraron fallos en la logica base.")
        sys.exit(1)

if __name__ == '__main__':
    main()
