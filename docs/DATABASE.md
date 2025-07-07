# Database table Information

## Tables

### Tickets

- Table name: `tickets`
- Purpose: Stores the primary state and metadata for each customer support ticket channel.

| Column Name | Data Type | Constraints | Description | Example |
| :--------------- | :--------------- | :--------------- | :------------------------------------- | :--------------- |
| id | SERIAL | PRIMARY KEY | The ticket id | 3 |
| channel_id | numeric(30) | NOT NULL | The discord channel id for the ticket | 12930514934123 |
| auto_timeout | INT | DEFAULT 48 | The auto timeout time for the ticket | 48 |
| timed_out | INT | [0,1] | Determines if the ticket has timed out | 1 |
| close_msg_id | numeric(30) | NOT NULL | The message id where the close channel button is attached | 12983719823748 |
| status | INT | [0,1,2,3] | The ticket status |  TicketStatus.OPEN |
| guild_id | numeric(30) | NOT NULL | The guild id where the ticket is located | 123984791823748 |

Note: The TicketStatus enum is defined as

```python
TicketStatus(Enum):
  OPEN=0
  IN_PROGRESS=1
  RESOLVED=2
  CLOSED=3
```

### Ticket Participants

- Table name: `ticket_participants`
- Purpose: Stores all the participants in a given ticket.

| Column Name | Data Type | Constraints | Description | Example |
| :--------------- | :--------------- | :--------------- | :--------------- | :--------------- |
| ticket_id | INT | FOREIGN KEY REFRENCES tickets(id) tickets(id) ON DELETE CASCADE  | The ticket id in database | 49 |
| participant_id | numeric(30) | NOT NULL | The discord user id of the ticket participant | 1293918324981293489 |

### Ticket panels

- Table name: `ticket_panels`
- Purpose: Stores the open ticket message in each guild and the message id.

| Column Name | Data Type | Constraints | Description | Example |
| :--------------- | :--------------- | :--------------- | :--------------- | :--------------- |
| guild_id | numeric(30) | NOT NULL PRIMARY KEY | The guild id that the ticket open message lives in | 18243798234 |
| channel_id | numeric(30) | NOT NULL | The channel id that the ticket open message lives in | 123098410982394 |
| message_id | numeric(30) | NOT NULL | The message id of the ticket open message | 410928340981290348 |

### Keywords

- Table name: `keywords`
- Purpose: Stores the keywords data.

| Column Name | Data Type | Constraints | Description | Example |
| :--------------- | :--------------- | :--------------- | :--------------- | :--------------- |
| id | SERIAL | PRIMARY KEY | The keyword id | 3 |
| trigger | VARCHAR | NOT NULL | The trigger of the keyword | "你好" |
| response | VARCHAR | none | The response of the keyword | "你好" |
| guild_id | numeric | NOT NULL | The guild id that the keyword is allowed to trigger | 102301230123 |
| kw_type | VARCHAR | NOT NULL = ANY ARRAY("句中","句首") | The keyword type | 句中 |
| in_ticket_only | BOOLEAN | NOT NULL | If the keyword should trigger in ticket only, defaults to true | true |
| mention_participants | BOOLEAN | NOT NULL | Whether the keyword response should mention the participant if triggered in a ticket channel, defaults to true | true |

Note: The (trigger,guild_id) is unique, meaning that a trigger is unique per guild.

```python
class KeywordType(StrEnum):
  MATCH_START = "句首"
  IS_SUBSTR = "句中"
```

### Keyword channels

- Table name: `keyword_channel`

| Column Name | Data Type | Constraints | Description | Example |
| :--------------- | :--------------- | :--------------- | :--------------- | :--------------- |
| keyword_id | bigserial | NOT NULL FOREIGN KEY REFRENCES keywords(id) | The keyword id | 20 |
| channel_id | numeric | NOT NULL | The id of the channel that the keyword should trigger in | 11349817298347 |
