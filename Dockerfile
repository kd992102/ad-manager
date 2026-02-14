FROM python:3.11-slim

WORKDIR /app

# 安裝必要的 OpenSSL 檔案
RUN apt-get update && apt-get install -y openssl && rm -rf /var/lib/apt/lists/*

# 核心：修改 OpenSSL 設定檔以啟用 Legacy Provider
RUN sed -i 's/providers = provider_sect/providers = provider_sect\n\n[provider_sect]\ndefault = default_sect\nlegacy = legacy_sect\n\n[default_sect]\nactivate = 1\n\n[legacy_sect]\nactivate = 1/g' /etc/ssl/openssl.cnf

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .
CMD ["python", "run.py"]
