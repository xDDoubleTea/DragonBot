# Database table Information

## Tables

### Tickets

- Table name: `tickets`
- Purpose: Stores the primary state and metadata for each customer support ticket channel.

| Column Name | Data Type | Constraints | Description | Example |
| :---------------:| :---------------: | :---------------: | :-------------------------------------:| :---------------: |
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
| --------------- | --------------- | --------------- | --------------- | --------------- |
| ticket_id | INT | FOREIGN KEY REFRENCES tickets(id) tickets(id) ON DELETE CASCADE  | The ticket id in database | 49 |
| participant_id | numeric(30) | NOT NULL | The discord user id of the ticket participant | 1293918324981293489 |
