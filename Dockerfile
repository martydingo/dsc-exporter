FROM debian
RUN mkdir /app
WORKDIR /app
RUN apt update && apt install -y python3 python3-pip python3-venv git
RUN python3 -m venv /app/venv
RUN /app/venv/bin/pip3 install git+https://github.com/DNS-OARC/dsc-datatool
RUN /app/venv/bin/pip3 install git+https://github.com/martydingo/dsc-exporter