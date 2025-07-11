<!--toc:start-->
- [Keyword System](#keyword-system)
  - [add_keyword](#addkeyword)
  - [remove_keyword](#removekeyword)
  - [keyword_edit](#keywordedit)
  - [keyword_list](#keywordlist)
  - [keyword_edit_channel](#keywordeditchannel)
<!--toc:end-->
# Keyword System

## add_keyword

**Usage:**  
`/add_keyword <trigger> <response> <response_type> [channel] [in_ticket_only] [mention_participants]`  
**Default Values:**  
channel: None, in_ticket_only: True, mention_participants: True  
**Permissions:**  
Has admin permission in the guild.  
**Description:**  
Add a keyword to the keyword system.  
**Parameter Descriptions:**  
trigger: The keyword trigger.  
response: The keyword response.  
response_type: The type of response, can be "句首" or "句中".  
channel: The channel to add the keyword to, defaults to None, which means where the keyword can be triggered is depended on the in_ticket_only parameter.
in_ticket_only: If the keyword can only be triggered in ticket channels, defaults to True.
mention_participants: If the keyword response should mention the participants in a ticket, defaults to True.

## remove_keyword

**Usage:**  
`/remove_keyword <trigger>`  
**Default Values:**  
None.  
**Permissions:**  
Has admin permission in the guild.  
**Description:**  
Remove a keyword from the keyword system.
**Parameter Descriptions:**  
trigger: The keyword trigger to remove.

## keyword_edit

**Usage:**  
`/keyword_edit <trigger> [response] [response_type] [in_ticket_only] [mention_participants]`  
**Default Values:**  
response: None, response_type: None, in_ticket_only: True, mention_participants: True  
**Permissions:**  
Has admin permission in the guild.  
**Description:**  
Edits an existing keyword. A modal will pop up to confirm the changes.  
**Parameter Descriptions:**  
trigger: The keyword trigger to edit.  
response: The new response. If not provided, the original response is kept.  
response_type: The new response type ("句首" or "句中"). If not provided, the original type is kept.  
in_ticket_only: Whether the keyword can only be triggered in ticket channels.  
mention_participants: Whether the response should mention participants in a ticket channel.  

## keyword_list

**Usage:**  
`/keyword_list`  
**Default Values:**  
None.  
**Permissions:**  
Has admin permission in the guild.  
**Description:**  
Displays a paginated list of all keywords configured for the server.  

## keyword_edit_channel

**Usage:**  
`/keyword_edit_channel <trigger> <channel> [add_or_remove]`  
**Default Values:**  
add_or_remove: None  
**Permissions:**  
Has admin permission in the guild.  
**Description:**  
Adds or removes a specific channel from a keyword's list of allowed channels. This is only effective if the keyword is not set to be "in_ticket_only".  
**Parameter Descriptions:**  
trigger: The keyword to modify.  
channel: The channel to add or remove.  
add_or_remove: The action to perform. Can be "加入" (Add) or "移除" (Remove).  
