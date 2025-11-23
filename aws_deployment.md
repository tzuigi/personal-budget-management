# AWS Deployment Guide pentru Aplicația de Gestionare Buget

## Descrierea infrastructurii

Aplicația "Buget Personal" este o aplicație Flask robustă care poate fi deployată în cloud AWS utilizând următoarea infrastructură optimizată. Aplicația include integrare AWS S3 opțională cu fallback local, ceea ce permite flexibilitate în deployment.

### Componente AWS utilizate:
1. **Amazon EC2**: Pentru hostarea aplicației Flask cu Gunicorn
2. **Amazon RDS**: Pentru baza de date PostgreSQL în producție (opțional - SQLite implicit)
3. **Amazon S3**: Pentru stocarea fișierelor de export (CSV, PDF) și backup-uri (opțional)
4. **Amazon CloudWatch**: Pentru monitorizarea, logging și alerte
5. **Application Load Balancer**: Pentru distribuirea traficului și SSL termination
6. **Amazon Route 53**: Pentru gestionarea DNS-ului (opțional)
7. **AWS Certificate Manager**: Pentru certificatele SSL/TLS
8. **Amazon VPC**: Pentru izolarea rețelei și securitate

### Arhitectura aplicației curente:
- **Rate limiting** implementat cu Flask-Limiter (suportă Redis sau memory backend)
- **Integrare S3** opțională prin `app/utils.py` cu fallback la stocarea locală
- **Export PDF** cu ReportLab pentru rapoarte complete cu grafice
- **Autentificare securizată** cu Flask-Login și protecție CSRF
- **Validare robustă** cu WTForms și Flask-WTF
- **Flexibilitate în configurare** prin variabile de mediu

## Pași pentru configurare

### 1. Configurarea bazei de date RDS (Opțional)

**Notă**: Aplicația folosește SQLite în mod implicit și funcționează perfect local. RDS este necesar doar pentru deployment în producție cu scalabilitate mare.

```bash
# Crearea unei instanțe de bază de date PostgreSQL pe RDS
aws rds create-db-instance \
    --db-instance-identifier budget-personal-db \
    --engine postgres \
    --allocated-storage 20 \
    --db-instance-class db.t3.micro \
    --master-username budget_admin \
    --master-user-password <parola_sigura> \
    --backup-retention-period 7 \
    --vpc-security-groups <id_grup_securitate> \
    --db-subnet-group <subnet_group> \
    --port 5432
```

### 2. Configurarea instanței EC2

```bash
# Lansarea unei instanțe EC2
aws ec2 run-instances \
    --image-id ami-0c55b159cbfafe1f0 \  # Amazon Linux 2 AMI
    --instance-type t2.micro \
    --key-name buget-personal-key \
    --security-group-ids <id_grup_securitate> \
    --subnet-id <subnet_id> \
    --user-data file://ec2-user-data.sh
```

### 3. Configurarea S3 pentru fișiere de export (Opțional)

**Notă**: Aplicația include fallback local în folderul `exports/` dacă S3 nu este configurat.

```bash
# Crearea unui bucket S3
aws s3 mb s3://buget-personal-exports

# Setarea politicii de acces pentru bucket
aws s3api put-bucket-policy \
    --bucket buget-personal-exports \
    --policy file://bucket-policy.json
```

### 4. Configurarea CloudWatch pentru logging

```bash
# Crearea unui grup de log-uri
aws logs create-log-group \
    --log-group-name budget-personal-logs

# Crearea unui stream de log-uri
aws logs create-log-stream \
    --log-group-name budget-personal-logs \
    --log-stream-name app-logs
```

## Script pentru instalarea dependențelor pe EC2 (ec2-user-data.sh)

```bash
#!/bin/bash
yum update -y
yum install -y python3 python3-pip git nginx
pip3 install --upgrade pip

# Clonarea repository-ului
cd /home/ec2-user
git clone https://github.com/user/APLICATIE_GESTIONARE_BUGET.git
cd APLICATIE_GESTIONARE_BUGET

# Instalarea dependențelor
pip3 install -r requirements.txt
pip3 install gunicorn psycopg2-binary  # Pentru PostgreSQL (opțional)

# Crearea folderului pentru exporturi locale
mkdir -p /home/ec2-user/APLICATIE_GESTIONARE_BUGET/exports
chown ec2-user:ec2-user /home/ec2-user/APLICATIE_GESTIONARE_BUGET/exports

# Configurarea Nginx
cat > /etc/nginx/conf.d/buget-personal.conf <<EOF
server {
    listen 80;
    server_name _;
    
    location /static {
        alias /home/ec2-user/APLICATIE_GESTIONARE_BUGET/app/static;
    }
    
    location / {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host \$host;
        proxy_set_header X-Real-IP \$remote_addr;
    }
}
EOF

# Restartarea Nginx
systemctl restart nginx
systemctl enable nginx

# Configurarea și pornirea aplicației cu Gunicorn
cat > /etc/systemd/system/buget-personal.service <<EOF
[Unit]
Description=Buget Personal Flask Application
After=network.target

[Service]
User=ec2-user
WorkingDirectory=/home/ec2-user/APLICATIE_GESTIONARE_BUGET
Environment="PATH=/home/ec2-user/APLICATIE_GESTIONARE_BUGET/venv/bin"
Environment="DATABASE_URL=sqlite:////home/ec2-user/APLICATIE_GESTIONARE_BUGET/budget.db"
Environment="SECRET_KEY=<cheie_secreta_sigura>"
Environment="AWS_ACCESS_KEY_ID=<access_key>"  # Opțional pentru S3
Environment="AWS_SECRET_ACCESS_KEY=<secret_key>"  # Opțional pentru S3
Environment="S3_BUCKET=buget-personal-exports"  # Opțional pentru S3
ExecStart=/home/ec2-user/APLICATIE_GESTIONARE_BUGET/venv/bin/gunicorn -w 4 -b 127.0.0.1:8000 run:app

[Install]
WantedBy=multi-user.target
EOF

# Pornirea serviciului
systemctl start buget-personal
systemctl enable buget-personal
```

## Configurarea producției în aplicația Flask

Aplicația este deja configurată pentru deployment în AWS prin următoarele caracteristici:

### 1. Configurația flexibilă în `config.py`

Aplicația suportă configurarea prin variabile de mediu pentru toate serviciile AWS:

```python
# Configurare AWS (toate opționale)
AWS_ACCESS_KEY_ID = os.environ.get('AWS_ACCESS_KEY_ID')
AWS_SECRET_ACCESS_KEY = os.environ.get('AWS_SECRET_ACCESS_KEY')  
S3_BUCKET = os.environ.get('S3_BUCKET')

# Configurare bază de date flexibilă
SQLALCHEMY_DATABASE_URI = (
    os.environ.get('DATABASE_URL') or 
    'sqlite:///' + os.path.join(BASE_DIR, 'budget.db')
)

# Configurare rate limiting cu Redis opțional
RATELIMIT_STORAGE_URL = os.environ.get('REDIS_URL') or 'memory://'
```

### 2. Integrarea S3 cu fallback local

Clasa `S3Util` din `app/utils.py` gestionează automat:
- Verificarea configurației AWS
- Utilizarea S3 când este disponibil
- Fallback la stocarea locală în `exports/` când AWS nu este configurat
- Logging complet pentru toate operațiile

### 3. Configurarea pentru producție

```bash
# Obligatorii pentru securitate
export SECRET_KEY="your-very-secure-secret-key-here"
export FLASK_ENV="production"

# Pentru baza de date PostgreSQL (opțional - implicit SQLite)
export DATABASE_URL="postgresql://username:password@rds-endpoint:5432/database"

# Pentru integrarea S3 (opțional - implicit stocare locală)
export AWS_ACCESS_KEY_ID="your-aws-access-key"
export AWS_SECRET_ACCESS_KEY="your-aws-secret-key"
export S3_BUCKET="buget-personal-exports"

# Pentru rate limiting avansat (opțional - implicit memory)
export REDIS_URL="redis://your-redis-endpoint:6379"

# Pentru logging în CloudWatch (opțional)
export LOG_TO_STDOUT="1"
```

### 4. Dependențe pentru producție

Aplicația include toate dependențele necesare în `requirements.txt`. Pentru AWS, instalați suplimentar:

```bash
# Pentru PostgreSQL (dacă utilizați RDS)
pip install psycopg2-binary

# Pentru Redis (dacă utilizați ElastiCache)  
pip install redis

# Pentru deployment cu Gunicorn
pip install gunicorn
```

## Testarea configurației

Înainte de deployment, testați configurația local:

```powershell
# Setați variabilele de mediu pentru test
$env:SECRET_KEY = "test-secret-key"
$env:FLASK_ENV = "production"

# Rulați aplicația
python run.py
```

## Verificarea funcționalității S3

Pentru a testa integrarea S3:

```python
# Testați în Python shell
from app import create_app
from app.utils import S3Util
import io

app = create_app()
with app.app_context():
    # Test upload
    test_data = io.BytesIO(b"test content")
    result = S3Util.upload_file(test_data, "test.txt")
    print(f"Upload result: {result}")
    
    # Test download  
    content = S3Util.download_file("test.txt")
    print(f"Downloaded: {content}")
```

### Implementarea funcționalității pentru S3

Aplicația include deja implementarea completă pentru integrarea S3 în fișierul `app/utils.py`. Clasa `S3Util` oferă:

**Caracteristici principale:**
- **Fallback inteligent**: Dacă AWS nu este configurat, fișierele sunt salvate local în `exports/`
- **Suport multiplu de tipuri**: Poate gestiona `bytes`, `str`, `io.BytesIO`, `io.StringIO`
- **Logging detaliat**: Înregistrează toate operațiile pentru debugging
- **Gestionarea erorilor**: Tratează elegant erorile de conectivitate sau configurare

**Utilizare:**
```python
from app.utils import S3Util

# Upload fișier (va folosi S3 sau local în funcție de configurare)
url = S3Util.upload_file(file_data, "exports/report.pdf")

# Download fișier (va căuta în S3 sau local)
content = S3Util.download_file("exports/report.pdf")
```

**Configurația necesară pentru S3 (în variabile de mediu):**
```bash
export AWS_ACCESS_KEY_ID=your_access_key
export AWS_SECRET_ACCESS_KEY=your_secret_key
export S3_BUCKET=buget-personal-exports
```

**Dacă nu este configurat AWS:**
- Fișierele vor fi salvate în folderul local `exports/`
- Aplicația va funcționa normal fără modificări de cod
- Mesaje de logging vor indica utilizarea stocării locale

## Script pentru CI/CD

Putem crea un workflow GitHub Actions pentru a automatiza deploymentul în AWS:

```yaml
name: Deploy to AWS

on:
  push:
    branches: [ main ]

jobs:
  deploy:
    runs-on: ubuntu-latest
    
    steps:
    - uses: actions/checkout@v2
    
    - name: Set up Python
      uses: actions/setup-python@v2
      with:
        python-version: '3.9'
    
    - name: Install dependencies
      run: |
        python -m pip install --upgrade pip
        if [ -f requirements.txt ]; then pip install -r requirements.txt; fi
        pip install pytest
      - name: Run tests
      run: |
        python tests.py
    
    - name: Configure AWS credentials
      uses: aws-actions/configure-aws-credentials@v1
      with:
        aws-access-key-id: ${{ secrets.AWS_ACCESS_KEY_ID }}
        aws-secret-access-key: ${{ secrets.AWS_SECRET_ACCESS_KEY }}
        aws-region: us-east-1
    
    - name: Deploy to EC2
      run: |
        # Generare arhivă pentru deployment
        zip -r deploy.zip . -x "*.git*" "venv/*" "__pycache__/*" "*.pyc"
        
        # Încărcare în S3
        aws s3 cp deploy.zip s3://buget-personal-deployments/
          # Executare script de deployment pe EC2
        aws ssm send-command \
          --document-name "AWS-RunShellScript" \
          --targets "Key=tag:Name,Values=buget-personal-app" \
          --parameters commands="cd /home/ec2-user && aws s3 cp s3://buget-personal-deployments/deploy.zip . && unzip -o deploy.zip -d APLICATIE_GESTIONARE_BUGET && cd APLICATIE_GESTIONARE_BUGET && pip install -r requirements.txt && mkdir -p exports && systemctl restart buget-personal"
```

## Configurarea HTTPS cu AWS Certificate Manager și Application Load Balancer

Pentru a configura HTTPS pentru aplicație, folosiți AWS Certificate Manager și Application Load Balancer:

```bash
# Crearea unui certificat SSL în ACM
aws acm request-certificate \
    --domain-name buget-personal.example.com \
    --validation-method DNS \
    --idempotency-token 1234 \
    --options CertificateTransparencyLoggingPreference=ENABLED

# După crearea certificatului, configurăm Route 53 pentru validare
# Înregistrăm certificatul în Load Balancer
aws elbv2 create-listener \
    --load-balancer-arn <load-balancer-arn> \
    --protocol HTTPS \
    --port 443 \
    --certificates CertificateArn=<certificate-arn> \
    --ssl-policy ELBSecurityPolicy-2016-08 \
    --default-actions Type=forward,TargetGroupArn=<target-group-arn>
```

Alternativ, pentru configurarea SSL direct pe instanța EC2, puteți folosi Let's Encrypt. Aplicația include deja un script `ssl_setup.sh` care poate fi adaptat pentru acest scop.

## Monitorizare și Alerte

Pentru monitorizarea aplicației, folosiți CloudWatch pentru alerte și dashboard-uri:

```bash
# Crearea unei alarme pentru utilizarea CPU ridicată
aws cloudwatch put-metric-alarm \
    --alarm-name budget-app-high-cpu \
    --alarm-description "Alertă pentru utilizare ridicată a CPU" \
    --metric-name CPUUtilization \
    --namespace AWS/EC2 \
    --statistic Average \
    --period 300 \
    --threshold 80 \
    --comparison-operator GreaterThanThreshold \
    --dimensions Name=InstanceId,Value=<instance-id> \
    --evaluation-periods 2 \
    --alarm-actions <sns-topic-arn>

# Crearea unei alarme pentru erori HTTP 5xx
aws cloudwatch put-metric-alarm \
    --alarm-name budget-app-5xx-errors \
    --alarm-description "Alertă pentru erori HTTP 5xx" \
    --metric-name HTTPCode_ELB_5XX_Count \
    --namespace AWS/ApplicationELB \
    --statistic Sum \
    --period 300 \
    --threshold 5 \
    --comparison-operator GreaterThanThreshold \
    --dimensions Name=LoadBalancer,Value=<load-balancer-name> \
    --evaluation-periods 1 \
    --alarm-actions <sns-topic-arn>
```

## Concluzii

Acest ghid oferă instrucțiunile complete pentru deployment-ul aplicației în infrastructura AWS. Caracteristicile cheie ale implementării:

### Avantaje ale implementării curente:
- **Flexibilitate maximă**: Funcționează local (SQLite + stocare locală) sau în cloud (RDS + S3)
- **Configurare simplă**: Toate serviciile AWS sunt opționale și configurabile prin variabile de mediu
- **Fallback inteligent**: Aplicația nu se oprește dacă AWS nu este disponibil
- **Scalabilitate**: Pregătită pentru Rate limiting cu Redis și monitorizare CloudWatch
- **Securitate**: Implementare completă cu CSRF, rate limiting și autentificare robustă

### Opțiuni de deployment:
1. **Minimal**: EC2 cu SQLite și stocare locală (cost minim)
2. **Standard**: EC2 + S3 pentru fișiere (scalabilitate medie)  
3. **Enterprise**: EC2 + RDS + S3 + Redis + CloudWatch (scalabilitate maximă)

### Recomandări pentru producție:
- Folosiți Application Load Balancer pentru distribuirea traficului
- Configurați Auto Scaling pentru gestionarea automată a capacității
- Implementați backup-uri regulate pentru baza de date și fișiere
- Monitorizați performanțele cu CloudWatch și setați alerte

Prin utilizarea serviciilor AWS, aplicația devine mai scalabilă, mai fiabilă și mai sigură, menținând în același timp flexibilitatea de a funcționa în medii diverse.
