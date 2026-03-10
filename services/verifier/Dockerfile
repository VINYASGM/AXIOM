# ============================================
# Stage 1: Build the Rust verifier binary
# ============================================
FROM rust:slim-bookworm AS builder

# Install Z3 development libraries and protobuf compiler
RUN apt-get update && apt-get upgrade -y && apt-get install -y \
    libz3-dev \
    protobuf-compiler \
    pkg-config \
    cmake \
    clang \
    libclang-dev \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Cache dependency builds
COPY Cargo.toml Cargo.lock ./
RUN mkdir src && echo "fn main() {}" > src/main.rs
RUN cargo build --release 2>/dev/null || true

# Copy actual source and build
COPY src/ src/
COPY proto/ proto/
COPY build.rs ./

# Force rebuild with real source
RUN touch src/main.rs && cargo build --release

# ============================================
# Stage 2: Minimal runtime image
# ============================================
FROM debian:bookworm-slim

# Install runtime dependencies for Z3
RUN apt-get update && apt-get upgrade -y && apt-get install -y \
    libz3-4 \
    ca-certificates \
    && rm -rf /var/lib/apt/lists/*

RUN groupadd -g 1000 appuser && \
    useradd -u 1000 -g appuser -s /bin/bash -m appuser

COPY --chown=appuser:appuser --from=builder /app/target/release/verifier /usr/local/bin/verifier

ENV VERIFIER_PORT=0.0.0.0:50051

USER appuser

EXPOSE 50051

ENTRYPOINT ["verifier"]
