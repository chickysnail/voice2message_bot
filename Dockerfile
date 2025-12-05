# Stage 1: Builder
FROM rust:1.71 as builder

WORKDIR /usr/src/app

# Copy manifests
COPY Cargo.toml Cargo.lock ./

# Create dummy main to cache dependencies
RUN mkdir src && \
    echo "fn main() { println!(\"dummy\"); }" > src/main.rs && \
    cargo build --release || true && \
    rm -rf src

# Copy actual source code
COPY . .

# Build the application
RUN cargo build --release

# Stage 2: Runtime
FROM debian:bookworm-slim

# Install CA certificates for HTTPS
RUN apt-get update && \
    apt-get install -y ca-certificates && \
    rm -rf /var/lib/apt/lists/*

# Create non-root user
RUN useradd -m -u 1000 appuser

WORKDIR /home/appuser

# Copy binary from builder
COPY --from=builder /usr/src/app/target/release/voice-transcriber-bot ./voice-transcriber-bot

# Copy example env file (optional)
COPY .env.example ./ 

# Set ownership
RUN chown appuser:appuser ./voice-transcriber-bot && \
    chmod +x ./voice-transcriber-bot

# Switch to non-root user
USER appuser

# Expose health check port
EXPOSE 8080

# Set default log level
ENV RUST_LOG=info

# Run the application
CMD ["./voice-transcriber-bot"]
