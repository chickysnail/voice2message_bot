use axum::{
    response::Json,
    routing::get,
    Router,
};
use serde_json::{json, Value};
use std::net::SocketAddr;
use tracing::info;

async fn health_handler() -> Json<Value> {
    Json(json!({"status": "ok"}))
}

pub async fn start_health_server(bind_addr: String, port: u16) -> anyhow::Result<()> {
    let app = Router::new().route("/health", get(health_handler));

    let addr: SocketAddr = format!("{}:{}", bind_addr, port).parse()?;
    info!("Health check server listening on {}", addr);

    let listener = tokio::net::TcpListener::bind(addr).await?;
    axum::serve(listener, app).await?;

    Ok(())
}
