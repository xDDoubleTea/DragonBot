
<!--toc:start-->
- [Ticket System](#ticket-system)
  - [open_ticket](#openticket)
  - [close_ticket](#closeticket)
  - [add_participant](#addparticipant)
  - [remove_participant](#removeparticipant)
  - [archive_ticket](#archiveticket)
  - [r (Canned Response)](#r-canned-response)
<!--toc:end-->

# Ticket System

This system manages customer support tickets through dedicated text channels.

## open_ticket

*(Admin Command)*

**Usage:**  
`/open_ticket`  
**Default Values:**  
None.  
**Permissions:**  
Administrator.  
**Description:**  
Generates the main ticket panel message in the current channel. This message contains buttons for users to create new support tickets. Only one panel should exist per server.

## close_ticket

*(Staff Command)*

**Usage:**  
`/close_ticket`  
**Default Values:**  
None.  
**Permissions:**  
Customer Service Role.  
**Description:**  
Generates a new message with controls to close the current ticket. This command can only be used within an active ticket channel.

## add_participant

*(Staff Command)*

**Usage:**  
`/add_participant <user>`  
**Default Values:**  
None.  
**Permissions:**  
Customer Service Role.  
**Description:**  
Adds another user or member to the current ticket channel, allowing them to view and participate in the conversation.  
**Parameter Descriptions:**  
user: The user to add to the ticket.

## remove_participant

*(Staff Command)*

**Usage:**  
`/remove_participant <user>`  
**Default Values:**  
None.  
**Permissions:**  
Customer Service Role.  
**Description:**  
Removes a user from the current ticket channel, revoking their access.  
**Parameter Descriptions:**  
user: The user to remove from the ticket.

## archive_ticket

*(Staff Command)*

**Usage:**  
`/archive_ticket`  
**Default Values:**  
None.  
**Permissions:**  
Customer Service Role.  
**Description:**  
Sends a archive of the ticket. Can only be used in a ticket channel.  
**Parameter Descriptions:**  
None

> Note: This command has a cooldown of 10 minutes as it will make a lot of API calls.

## r (Canned Response)

*(Staff Command)*

**Usage:**  
`/r <reply>`  
**Default Values:**  
None.  
**Permissions:**  
Customer Service Role.  
**Description:**  
Sends a pre-written, canned response into the current ticket channel. This is used to quickly answer common questions.  
**Parameter Descriptions:**  
reply: The specific canned response to send, chosen from a pre-defined list.  
