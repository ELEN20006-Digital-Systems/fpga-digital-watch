FROM ubuntu:24.04

ENV DEBIAN_FRONTEND=noninteractive

RUN sed -i 's|archive.ubuntu.com|mirror.aarnet.edu.au|' /etc/apt/sources.list.d/ubuntu.sources

RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    git \
    wget \
    curl \
    make \
    python3 \
    python3-pip \
    python3-venv \
    libpython3-dev \
    iverilog \
    verilator \
    perl-doc \
    yosys \
    graphviz \
    z3 \
    locales \
    ca-certificates \
    && rm -rf /var/lib/apt/lists/*

RUN locale-gen en_AU.UTF-8
ENV LANG=en_AU.UTF-8
ENV LC_ALL=en_AU.UTF-8

WORKDIR /workspace

RUN python3 -m venv /opt/venv
ENV PATH="/opt/venv/bin:${PATH}"
RUN pip install --no-cache-dir --upgrade pip \
    && pip install --no-cache-dir cocotb==2.0.1 pytest==9.0.3 pytest-html==4.2.0 click==8.3.2

COPY --chmod=0755 sby/bin/sby /usr/local/bin/sby
COPY sby/share /usr/local/share

ARG TARGETARCH
RUN --mount=type=bind,source=arch,target=/archs \
    if [ -d "/archs/$TARGETARCH" ]; then \
      install -m 0755 /archs/$TARGETARCH/bin/* /usr/local/bin/; \
    else \
      echo "No binaries for TARGETARCH=$TARGETARCH"; \
    fi
    