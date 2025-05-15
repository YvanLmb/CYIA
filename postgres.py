import psycopg2

def connect_db():
    return psycopg2.connect(
        host="localhost",
        database="cyia_db",
        user="postgres",
        password="YVANDU78"
    )

conn = connect_db()
cur = conn.cursor()
cur.execute("SELECT version();")
print("✅ Connexion réussie :", cur.fetchone())

cur.close()
conn.close()
