-- name: create_conversation!
insert into conversation (id)
    values (:id);

-- name: add_message!
insert into message (conversation_id, role, message_index, content)
    values (:conversation_id, :role, coalesce((
            select
                max(message_index) + 1
            from message
            where
                conversation_id = :conversation_id), 0), :content);

-- name: get_last_messages
select
    role,
    content
from (
    select
        role,
        content
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
    created_at
from
    conversation
where
    id = :id;

