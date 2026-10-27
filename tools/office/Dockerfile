# 문서 변환용 (docx·pptx → PDF, 목차 갱신, 미리보기 이미지)
FROM ubuntu:24.04
RUN apt-get update && DEBIAN_FRONTEND=noninteractive apt-get install -y --no-install-recommends \
      libreoffice-writer libreoffice-impress libreoffice-script-provider-python python3-uno \
      fonts-nanum fonts-noto-cjk poppler-utils && rm -rf /var/lib/apt/lists/*
