from openai import OpenAI
import pandas as pd
import psycopg2
import os
from postgres import connect_db
import time

# 🔐 Remplace par ta clé d'API
openai_client = OpenAI(
    api_key=os.getenv("OPENAI_API_KEY")
)

# Catégories à prédire
LABELS = [
    "cours", "réclamation", "entreprise",
    "spam", "sondage", "association", "administratif","plateforme", "autres"
]

PROMPT_TEMPLATE = """
- cours : e-mails liés aux matières, enseignants, plannings, ou contenu pédagogique
- réclamation : messages de plaintes, signalements d’erreurs, demandes de corrections
- entreprise : messages d’entreprises (offres, partenariats, conférences)
- spam : contenu non pertinent, publicité, arnaques
- sondage : questionnaires, formulaires d’enquête, votes
- association : clubs, événements étudiants, organisations internes
- administratif : relances de documents, convocations, informations générales de l’école
- plateforme : notifications de sites comme Canvas, Kaggle, etc.
- autres : tout ce qui ne rentre pas dans les catégories précédentes

Réponds uniquement avec le nom exact d'une seule catégorie.

Exemple de format :
Objet : ...
Corps : ...

Catégorie : ...
"""



def fetch_emails_for_annotation(limit=900):
    conn = connect_db()
    cur = conn.cursor()
    cur.execute("""
        SELECT id, subject, body 
        FROM emails 
        WHERE category IS NULL 
        AND subject IS NOT NULL AND body IS NOT NULL 
        LIMIT %s;
    """, (limit,))
    data = cur.fetchall()
    cur.close()
    conn.close()
    return data

def classify_with_gpt(subject, body):
    prompt = PROMPT_TEMPLATE + f"\nObjet : {subject}\nCorps : {body[:1000]}\nCatégorie :"
    try:
        response = openai_client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[{"role": "user", "content": prompt}],
            temperature=0
        )
        label = response.choices[0].message.content.strip().lower()
        if label not in LABELS:
            return "autres"
        return label
    except Exception as e:
        print("Erreur GPT:", e)
        return "autres"

def update_email_category(email_id, category):
    conn = connect_db()
    cur = conn.cursor()
    cur.execute("UPDATE emails SET category = %s WHERE id = %s;", (category, email_id))
    conn.commit()
    cur.close()
    conn.close()

def annotate_emails():
    emails = fetch_emails_for_annotation(limit=1000)
    for idx, (eid, subject, body) in enumerate(emails):
        print(f"\n📨 E-mail {idx+1}/800 — ID {eid}")
        print("Objet :", subject)
        label = classify_with_gpt(subject, body)
        print("🧠 Catégorie :", label)
        update_email_category(eid, label)
        time.sleep(1.2)  # pour respecter les limites OpenAI

    print("\n✅ Annotation terminée ! Les 1000 e-mails ont été classés.")

if __name__ == "__main__":
    annotate_emails()
