-- Conversations table
create table conversation (
    id text primary key, -- UUID as text
    created_at timestamp not null default current_timestamp,
    title text not null
);

-- Messages within a conversation
create table message (
    id integer primary key autoincrement,
    conversation_id text not null,
    role text not null check (role in ('user', 'assistant')),
    message_index integer not null, -- Order within the conversation
    content text not null, -- Text or markdown
    created_at timestamp not null default current_timestamp,
    foreign key (conversation_id) references conversation (id),
    unique (conversation_id, message_index)
);

