# Database table Information

<!--toc:start-->
- [Database table Information](#database-table-information)
  - [Tables](#tables)
    - [Tickets](#tickets)
    - [Ticket Participants](#ticket-participants)
    - [Ticket panels](#ticket-panels)
    - [Keywords](#keywords)
    - [Keyword channels](#keyword-channels)
<!--toc:end-->

## Tables

### Tickets

- Table name: `tickets`
- Purpose: Stores the primary state and metadata for each customer support ticket channel.

| Column Name    | Data Type   | Constraints              | Description                                               |
|:---------------|:------------|:-------------------------|:----------------------------------------------------------|
| id             | SERIAL      | PRIMARY KEY              | The ticket id                                             |
| channel_id     | numeric(30) | NOT NULL                 | The discord channel id for the ticket                     |
| auto_timeout   | INT         | DEFAULT 48               | The auto timeout time for the ticket                      |
| timed_out      | INT         | \[0,1\] DEFAULT 0        | Determines if the ticket has timed out                    |
| close_msg_id   | numeric(30) | NOT NULL                 | The message id where the close channel button is attached |
| close_msg_type | numeric(30) | NOT NULL \[0,1,2\]       | The close message type                                    |
| status         | INT         | \[0,1,2,3\]              | The ticket status                                         |
| guild_id       | numeric(30) | NOT NULL                 | The guild id where the ticket is located                  |
| ticket_type    | VARCHAR     | \["代購","群組","其他"\] | The ticket type                                           |

Note: The TicketStatus enum is defined as

```python
class TicketStatus(Enum):
    """
    Represents the status of a ticket
    """

    OPEN = (0, "待處理")
    IN_PROGRESS = (1, "處理中")
    RESOLVED = (2, "處理完畢")
    CLOSED = (3, "已關閉")

    def __init__(self, id: int, string_repr: str):
        self.id = id
        self.string_repr = string_repr

    @classmethod
    def from_id(cls, status_id: int) -> "TicketStatus":
        """
        Looks up an enum member by its integer ID.
        Returns the TicketStatus member or None if the ID is not found.
        """
        # This is an efficient reverse lookup.
        # We iterate through all members of the class (`cls`) and check their `id` attribute.
        for member in cls:
            if member.id == status_id:
                return member
        return cls.OPEN  # Defaults to OPEN if no match is found, for safety.

```

### Ticket Participants

- Table name: `ticket_participants`
- Purpose: Stores all the participants in a given ticket.

| Column Name    | Data Type   | Constraints                                                     | Description                                   |
|:---------------|:------------|:----------------------------------------------------------------|:----------------------------------------------|
| ticket_id      | INT         | FOREIGN KEY REFRENCES tickets(id) tickets(id) ON DELETE CASCADE | The ticket id in database                     |
| participant_id | numeric(30) | NOT NULL                                                        | The discord user id of the ticket participant |

### Ticket panels

- Table name: `ticket_panels`
- Purpose: Stores the open ticket message in each guild and the message id.

| Column Name | Data Type   | Constraints          | Description                                          |
|:------------|:------------|:---------------------|:-----------------------------------------------------|
| guild_id    | numeric(30) | NOT NULL PRIMARY KEY | The guild id that the ticket open message lives in   |
| channel_id  | numeric(30) | NOT NULL             | The channel id that the ticket open message lives in |
| message_id  | numeric(30) | NOT NULL             | The message id of the ticket open message            |

### Keywords

- Table name: `keywords`
- Purpose: Stores the keywords data.

| Column Name          | Data Type | Constraints                         | Description                                                                                                    |
|:---------------------|:----------|:------------------------------------|:---------------------------------------------------------------------------------------------------------------|
| id                   | SERIAL    | PRIMARY KEY                         | The keyword id                                                                                                 |
| trigger              | VARCHAR   | NOT NULL                            | The trigger of the keyword                                                                                     |
| response             | VARCHAR   | none                                | The response of the keyword                                                                                    |
| guild_id             | numeric   | NOT NULL                            | The guild id that the keyword is allowed to trigger                                                            |
| kw_type              | VARCHAR   | NOT NULL = ANY ARRAY("句中","句首") | The keyword type                                                                                               |
| in_ticket_only       | BOOLEAN   | NOT NULL                            | If the keyword should trigger in ticket only, defaults to true                                                 |
| mention_participants | BOOLEAN   | NOT NULL                            | Whether the keyword response should mention the participant if triggered in a ticket channel, defaults to true |

Note: The (trigger,guild_id) is unique, meaning that a trigger is unique per guild.

```python
class KeywordType(StrEnum):
  MATCH_START = "句首"
  IS_SUBSTR = "句中"
```

### Keyword channels

- Table name: `keyword_channel`

| Column Name | Data Type | Constraints                                 | Description                                              |
|:------------|:----------|:--------------------------------------------|:---------------------------------------------------------|
| keyword_id  | bigserial | NOT NULL FOREIGN KEY REFRENCES keywords(id) | The keyword id                                           |
| channel_id  | numeric   | NOT NULL                                    | The id of the channel that the keyword should trigger in |
