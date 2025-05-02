-- Conversations table
create table conversation (
    id text primary key, -- UUID as text
    created_at timestamp not null default current_timestamp,
    title text not null
);

create table message (
    id integer primary key AUTOINCREMENT,
    conversation_id text not null,
    role TEXT not null check (role in ('user', 'assistant')),
    message_index integer not null,
    content text not null,
    created_at timestamp not null default current_timestamp,
    foreign key (conversation_id) references conversation (id) on delete cascade,
    unique (conversation_id, message_index)
);

