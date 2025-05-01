-- name: create_conversation!
insert into conversation (id, created_at, title)
    values (:id, current_timestamp, :title);

-- name: add_message!
insert into message (conversation_id, role, message_index, content, created_at)
    values (:conversation_id, :role, coalesce((
            select
                max(message_index) + 1
            from message
            where
                conversation_id = :conversation_id), 0), :content, current_timestamp);

-- name: get_last_messages
select
    role,
    content,
    created_at
from (
    select
        role,
        content,
        created_at
    from
        message
    where
        conversation_id = :conversation_id
    order by
        message_index desc
    limit :limit)
order by
    message_index asc;

-- name: get_conversation^
select
    id,
    created_at,
    title
from
    conversation
where
    id = :id;

