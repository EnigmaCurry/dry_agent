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

-- name: get_conversation_with_messages
select
    c.id as conversation_id,
    c.created_at as conversation_created_at,
    c.title as conversation_title,
    m.role as message_role,
    m.content as message_content,
    m.created_at as message_created_at,
    m.message_index as message_index
from
    conversation c
    left join message m on m.conversation_id = c.id
where
    c.id = :id
order by
    m.message_index asc;

-- name: get_conversations_with_first_sentence_paginated
select
    c.id,
    c.title,
    c.created_at,
    case when length(first_sentence) > 100 then
        substr(first_sentence, 1, 100) || '...'
    else
        first_sentence
    end as preview
from
    conversation c
    join (
        select
            m1.conversation_id,
            substr(m1.content, 1, instr (m1.content || '.', '.') - 1) as first_sentence
        from
            message m1
        where
            message_index = (
                select
                    min(m2.message_index)
                from
                    message m2
                where
                    m2.conversation_id = m1.conversation_id)) m on m.conversation_id = c.id
order by
    c.created_at desc
limit :page_size offset :offset;

