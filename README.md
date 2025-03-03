# dry_agent

dry_agent is a ChatOps bot and agent for d.rymcg.tech. The bot sits in
a Matrix room which you can chat with to manage your Docker server.

The user is able to ask questions and perform the following
tasks:

 * "Which services are running?"
 * "Start whoami and immich and then turn them off after 45 minutes."
 
Stretch goals include:
 
 * "Configure a new postgres database." and answer followup questions
   posed by the bot.
 
The chat bot may run on any machine where it has access to an LLM,
used to build a [structured JSON
message](https://lmstudio.ai/docs/api/structured-output) based on
information provided by the user. Once the user confirms the action,
it posts the message to an MQTT server that the agent receives from.

The agent must run on a secure workstation that has access to an
unlocked SSH key that controls your Docker server, and receives its
instructions via MQTT, which may include starting and stopping
services as well as status requests.

## Structured Responses

```
{
  "message_type": "string",  // "chat", "action", or "confirmation"
  "content": {},             // Content varies based on message_type
  "conversation_id": "string" // To track multi-turn interactions
}
```

### General chat responses (no Docker action)

```
{
  "message_type": "chat",
  "content": {
    "text": "I'm your Docker management assistant. I can help you start, stop, and check the status of your containers."
  },
  "conversation_id": "abc123"
}
```

### Docker actions

```
{
  "message_type": "action",
  "content": {
    "action_type": "string",  // "status", "start", "stop", "restart", "configure"
    "services": ["service1", "service2"],  // Array of service names
    "parameters": {  // Optional parameters specific to action_type
      "timeout": 45,  // Minutes
      "schedule": "2023-11-15T14:30:00Z"  // ISO 8601 timestamp
    },
    "confirmation_required": true  // Whether user confirmation is needed
  },
  "conversation_id": "abc123"
}
```

### Confirmations

```
{
  "message_type": "confirmation",
  "content": {
    "action_id": "action123",
    "description": "I'm about to start whoami and immich containers, then stop them after 45 minutes. Is this correct?",
    "action_details": {
      // Original action content copied here for reference
    }
  },
  "conversation_id": "abc123"
}
```

## Examples

"Which services are running?"

```
{
  "message_type": "action",
  "content": {
    "action_type": "status",
    "services": ["whoami", "immich"],
    "parameters": {},
    "confirmation_required": false
  },
  "conversation_id": "abc123"
}
```


"Start whoami and immich and then turn them off after 45 minutes."

```
{
  "message_type": "confirmation",
  "content": {
    "action_id": "action456",
    "description": "I'll start the whoami and immich containers, and automatically stop them after 45 minutes. Would you like me to proceed?",
    "action_details": {
      "action_type": "start_with_timeout",
      "services": ["whoami", "immich"],
      "parameters": {
        "timeout": 45
      }
    }
  },
  "conversation_id": "abc123"
}
```


"Configure a new postgres database."

```
{
  "message_type": "action",
  "content": {
    "action_type": "configure",
    "services": ["postgres"],
    "parameters": {
      "configuration_type": "new_database",
      "needs_additional_info": true,
      "required_parameters": ["hostname", "user", "password"]
    },
    "confirmation_required": true
  },
  "conversation_id": "abc123"
}
```
