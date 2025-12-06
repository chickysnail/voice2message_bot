use std::sync::Arc;
use teloxide::{
    dispatching::UpdateFilterExt, prelude::*, types::Update, utils::command::BotCommands,
};
use tokio::sync::Semaphore;
use tracing::info;

use crate::{
    bot::handlers::{
        handle_callback_query, handle_help, handle_settings, handle_start, handle_voice_message,
    },
    chat_completion::ChatCompletionClient,
    config::Config,
    storage::FileStore,
    transcriber::Transcriber,
    transcription_store::TranscriptionStore,
};

pub async fn run_bot(
    bot: Bot,
    config: Arc<Config>,
    transcriber: Arc<dyn Transcriber>,
    file_store: Arc<FileStore>,
    semaphore: Arc<Semaphore>,
    chat_client: Arc<ChatCompletionClient>,
    transcription_store: TranscriptionStore,
) {
    info!("Starting Telegram bot with long polling...");

    let handler = Update::filter_message()
        .branch(
            dptree::entry()
                .filter_command::<Command>()
                .endpoint(command_handler),
        )
        .branch(
            dptree::filter(|msg: Message| msg.voice().is_some() || msg.audio().is_some())
                .endpoint(voice_handler),
        );

    let callback_handler = Update::filter_callback_query().endpoint(handle_callback_query);

    let mut dispatcher = Dispatcher::builder(bot, handler.chain(callback_handler))
        .dependencies(dptree::deps![config, transcriber, file_store, semaphore, chat_client, transcription_store])
        .enable_ctrlc_handler()
        .build();

    dispatcher.dispatch().await;
}

#[derive(BotCommands, Clone)]
#[command(rename_rule = "lowercase", description = "Supported commands:")]
enum Command {
    #[command(description = "Display welcome message")]
    Start,
    #[command(description = "Display help information")]
    Help,
    #[command(description = "Show current settings")]
    Settings,
}

async fn command_handler(
    bot: Bot,
    msg: Message,
    cmd: Command,
    config: Arc<Config>,
) -> ResponseResult<()> {
    match cmd {
        Command::Start => handle_start(bot, msg).await,
        Command::Help => handle_help(bot, msg).await,
        Command::Settings => handle_settings(bot, msg, config).await,
    }
}

async fn voice_handler(
    bot: Bot,
    msg: Message,
    config: Arc<Config>,
    transcriber: Arc<dyn Transcriber>,
    file_store: Arc<FileStore>,
    semaphore: Arc<Semaphore>,
    transcription_store: TranscriptionStore,
) -> ResponseResult<()> {
    handle_voice_message(bot, msg, config, transcriber, file_store, semaphore, transcription_store).await
}
