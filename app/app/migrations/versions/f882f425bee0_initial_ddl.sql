-- Conversation metadata
create table conversation (
    id text primary key, -- UUID (as TEXT for portability)
    created_at timestamp default current_timestamp
);

-- Messages within a conversation
create table message (
    id integer primary key AUTOINCREMENT,
    conversation_id text not null,
    role TEXT check (role in ('user', 'assistant')) not null,
    message_index integer not null, -- Order within the conversation
    content text not null, -- Message content (text or markdown)
    created_at timestamp default current_timestamp,
    foreign key (conversation_id) references conversation (id),
    unique (conversation_id, message_index) -- Prevent duplicate indexes per conversation
);

