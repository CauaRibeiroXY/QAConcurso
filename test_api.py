#!/usr/bin/env python3
"""
Script de teste para verificar se a API de resultados está funcionando
"""

import requests
import json

def test_api_resultados():
    """Testa a API de resultados"""
    try:
        # Primeiro, fazer login
        session = requests.Session()
        
        # Tentar acessar a página de login
        login_response = session.get('http://127.0.0.1:5000/login')
        print(f"Login page status: {login_response.status_code}")
        
        # Tentar acessar a API sem autenticação (deve redirecionar)
        api_response = session.get('http://127.0.0.1:5000/api/resultados')
        print(f"API status (sem auth): {api_response.status_code}")
        print(f"URL final: {api_response.url}")
        
        return api_response.status_code
        
    except Exception as e:
        print(f"Erro no teste: {e}")
        return False

if __name__ == "__main__":
    print("Testando API de resultados...")
    result = test_api_resultados()
    print(f"Resultado do teste: {result}")
