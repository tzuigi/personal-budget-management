# Aplicație de Gestionare a Bugetului Personal

## Descriere

Aplicația de gestionare a bugetului personal este o platformă web robustă care ajută utilizatorii să își planifice și să își urmărească cheltuielile și economiile. Oferă o interfață intuitivă pentru adăugarea și clasificarea veniturilor și cheltuielilor, vizualizarea rapoartelor detaliate și stabilirea de bugete cu monitorizare în timp real.

## Tehnologii utilizate

- **Backend**: Flask (Python 3.8+)
- **Bază de date**: SQLite (SQLAlchemy ORM)
- **Frontend**: HTML5, CSS3, Bootstrap 5, JavaScript
- **Vizualizări de date**: Chart.js
- **Autentificare**: Flask-Login cu rate limiting
- **Validare formulare**: Flask-WTF, WTForms
- **Export PDF**: ReportLab
- **Cloud Storage**: AWS S3 (boto3)
- **Rate Limiting**: Flask-Limiter

## Funcționalități

### Autentificare și Securitate
- Înregistrare și autentificare utilizatori cu validare email
- Rate limiting pentru protecție împotriva atacurilor brute-force
- Gestionarea sesiunilor securizate cu Flask-Login
- Parolă criptată și validare robustă

### Gestionarea Tranzacțiilor
- Adăugare, editare și ștergere tranzacții (venituri și cheltuieli)
- Clasificarea tranzacțiilor pe categorii personalizabile cu culori
- Filtrarea avansată după perioadă, categorie, tip și valoare
- Căutare în tranzacții după descriere
- Paginarea rezultatelor pentru performanță optimă

### Gestionarea Categoriilor
- Crearea categoriilor personalizate cu culori distinctive
- Separarea categoriilor pe tip (venituri/cheltuieli)
- Editarea și ștergerea categoriilor cu verificări de integritate

### Bugete și Monitorizare
- Setarea bugetelor lunare pe categorii
- Monitorizarea progresului bugetului în timp real
- Alerte vizuale pentru bugetele depășite
- Calcularea procentajului de utilizare a bugetului

### Rapoarte și Vizualizări
- Dashboard comprehensive cu statistici financiare
- Grafice interactive cu Chart.js (pie charts, bar charts)
- Analiza veniturilor vs. cheltuielilor
- Distribuția cheltuielilor pe categorii
- Evoluția financiară în timp

### Import/Export și Backup
- Export tranzacții în format CSV cu filtrare avansată
- Generare rapoarte PDF complete cu grafice și statistici
- Import tranzacții din fișiere CSV cu validare și preview
- Integrare AWS S3 opțională pentru stocarea fișierelor (fallback local)
- Stocarea automată în folderul local `exports/` când AWS nu este configurat

### Interfață Utilizator
- Design responsive cu Bootstrap 5
- Interfață intuitivă și ușor de folosit
- Notificări flash pentru feedback utilizator
- Validare JavaScript în timp real
- Teme de culori și iconuri moderne

## Structura proiectului

```
APLICATIE_GESTIONARE_BUGET/
│
├── app/                          # Pachetul principal al aplicației
│   ├── __init__.py              # Configurarea și inițializarea aplicației Flask
│   ├── models.py                # Modele SQLAlchemy (User, Category, Transaction, Budget)
│   ├── forms.py                 # Formulare WTF pentru validare și interacțiune
│   ├── routes.py                # Rute și logica aplicației (auth, dashboard, CRUD)
│   ├── utils.py                 # Utilități AWS S3 cu fallback local
│   ├── static/                  # Fișiere statice
│   │   ├── css/                 # Stiluri CSS personalizate
│   │   ├── js/                  # JavaScript pentru interactivitate
│   │   └── uploads/             # Fișiere încărcate temporar
│   └── templates/               # Template-uri Jinja2
│       ├── base.html           # Template de bază cu Bootstrap 5
│       ├── auth/               # Template-uri pentru autentificare
│       │   ├── login.html      # Formular de autentificare
│       │   └── register.html   # Formular de înregistrare
│       ├── index.html          # Dashboard principal cu grafice
│       ├── transactions.html   # Gestionare tranzacții
│       ├── categories.html     # Gestionare categorii
│       ├── budgets.html        # Gestionare bugete
│       ├── reports.html        # Rapoarte și analize
│       └── import_transactions.html # Import tranzacții CSV
│
├── config.py                    # Configurare aplicație (dev/prod/AWS)
├── requirements.txt             # Dependențe Python (Flask, SQLAlchemy, etc.)
├── run.py                       # Punct de intrare pentru aplicație
├── init_db.py                   # Script pentru inițializarea bazei de date
├── tests.py                     # Suite de teste unitare
├── exports/                     # Folderul pentru fișiere exportate (CSV, PDF)
├── aws_deployment.md           # Ghid pentru deployment în AWS
└── README.md                   # Documentația proiectului
```

## Instalare și configurare

### Cerințe preliminare

- Python 3.8+ (recomandat Python 3.9+)
- pip (Python package installer)
- Git (pentru clonarea repository-ului)

### Pași de instalare

1. **Clonează repository-ul:**
```bash
git clone <repository-url>
cd APLICATIE_GESTIONARE_BUGET
```

2. **Creează și activează mediul virtual:**
```bash
# Windows
python -m venv venv
venv\Scripts\activate

# Linux/macOS
python3 -m venv venv
source venv/bin/activate
```

3. **Instalează dependențele:**
```bash
pip install -r requirements.txt
```

4. **Configurează variabilele de mediu (opțional pentru AWS S3):**
```bash
# Pentru integrarea AWS S3 (opțional - aplicația funcționează și fără)
export AWS_ACCESS_KEY_ID=your_access_key
export AWS_SECRET_ACCESS_KEY=your_secret_key
export S3_BUCKET_NAME=your_bucket_name

# Fără configurația AWS, fișierele vor fi salvate local în folderul exports/
```

5. **Inițializează baza de date:**
```bash
python init_db.py
```

6. **Rulează testele (opțional):**
```bash
python tests.py
```

7. **Pornește aplicația:**
```bash
python run.py
```

Aplicația va fi disponibilă la adresa `http://localhost:5000/`.

### Configurație pentru producție

Pentru deployment în producție, modifică configurația în `config.py`:
- Setează `SECRET_KEY` la o valoare sigură din variabile de mediu
- Configurează conexiunea la baza de date PostgreSQL pentru AWS RDS (opțional)
- Activează logging-ul pentru CloudWatch (în caz de deployment AWS)
- Configurează Redis pentru rate limiting în producție (opțional)

## Utilizare

### Primul pas - Configurarea contului
1. Accesează aplicația la `http://localhost:5000/`
2. Creează un cont nou completând formularul de înregistrare
3. Autentifică-te cu credențialele create

### Configurarea categoriilor
1. Navigheaza la secțiunea "Categorii"
2. Adaugă categoriile pentru venituri (Salariu, Freelancing, etc.)
3. Adaugă categoriile pentru cheltuieli (Mâncare, Transport, Utilități, etc.)
4. Personalizează culorile pentru fiecare categorie

### Gestionarea tranzacțiilor
1. Folosește butonul "Adaugă Tranzacție" din dashboard
2. Completează formularul cu suma, categoria și descrierea
3. Folosește filtrele pentru a găsi tranzacții specifice
4. Editează sau șterge tranzacțiile din lista detaliată

### Configurarea bugetelor
1. Accesează secțiunea "Bugete"
2. Setează limite lunare pentru fiecare categorie de cheltuieli
3. Monitorizează progresul în dashboard-ul principal
4. Primește alerte vizuale când bugetul este depășit

### Rapoarte și analize
1. Vizualizează statisticile în dashboard-ul principal cu grafice interactive
2. Folosește filtrele pentru analiza detaliată pe perioade specifice
3. Exportă rapoartele în format PDF pentru arhivare și prezentare
4. Descarcă datele în CSV pentru analize externe sau backup
5. Monitorizează progresul bugetelor și primește alerte vizuale

## Implementare în AWS

Pentru instrucțiuni detaliate despre implementarea în producție pe AWS, consultă fișierul [aws_deployment.md](aws_deployment.md). Aplicația suportă:
- Deployment pe Amazon EC2 cu Gunicorn
- Integrare cu Amazon S3 pentru stocarea fișierelor
- Configurare pentru Amazon RDS (PostgreSQL)
- Monitorizare cu Amazon CloudWatch

## Contribuție

Dacă dorești să contribui la acest proiect, te rugăm să urmezi acești pași:

1. Fork repository-ul
2. Creează un branch pentru funcționalitatea ta (`git checkout -b feature/amazing-feature`)
3. Asigură-te că testele trec (`python tests.py`)
4. Commit schimbările (`git commit -m 'Add some amazing feature'`)
5. Push branch-ul (`git push origin feature/amazing-feature`)
6. Deschide un Pull Request

### Ghiduri pentru dezvoltare
- Urmează standardele PEP 8 pentru codul Python
- Adaugă teste pentru funcționalitățile noi
- Documentează orice modificări în README
- Testează compatibilitatea cu Python 3.8+

## Licență

Acest proiect este dezvoltat în scop educațional pentru cursul "Metode de Dezvoltare Software".

## Autor

Dezvoltat ca proiect pentru cursul "Metode de Dezvoltare Software" de la Facultatea de Matematică și Informatică.

## Suport și Contact

Pentru întrebări sau probleme:
- Creează un Issue în repository
- Consultă documentația din fișierul `aws_deployment.md` pentru deployment
- Verifică fișierul `tests.py` pentru exemple de utilizare