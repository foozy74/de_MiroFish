import os
import sys
import sqlite3

# Pfad zum Backend-Ordner hinzufügen
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))

from app.tenant.db import register_tenant, upsert_tenant_api_key

def setup_local():
    print("--- MiroFish Local Setup ---")
    
    # 1. Tenant registrieren
    clerk_id = os.environ.get("TEST_CLERK_ORG_ID", "org_test_local")
    display_name = "Local Test Org"
    
    print(f"Registriere Tenant: {display_name} ({clerk_id})...")
    tenant_id = register_tenant(clerk_id, display_name)
    print(f"Tenant erfolgreich registriert. Interne ID: {tenant_id}")
    
    # 2. Optional: OpenAI API Key für diesen Tenant hinterlegen
    openai_key = os.environ.get("OPENAI_API_KEY")
    if openai_key:
        print("Speichere OpenAI API Key in der verschlüsselten Tenant-Datenbank...")
        upsert_tenant_api_key(tenant_id, "OPENAI_API_KEY", openai_key)
        print("Key erfolgreich hinterlegt.")
    else:
        print("Hinweis: Kein OPENAI_API_KEY in der Umgebung gefunden. Key muss später über das UI hinterlegt werden.")

    print("\nSetup abgeschlossen!")
    print(f"Du kannst nun API-Anfragen mit dem Header 'Authorization: {clerk_id}' (oder via Clerk JWT) stellen.")

if __name__ == "__main__":
    setup_local()
