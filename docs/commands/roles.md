<!--toc:start-->
- [Role Requesting System](#role-requesting-system)
  - [role_config set_channel](#roleconfig-setchannel)
  - [role_config add_requestable_role](#roleconfig-addrequestablerole)
  - [role_config remove_requestable_role](#roleconfig-removerequestablerole)
  - [check_request_status](#checkrequeststatus)
  - [check_requestable_roles](#checkrequestableroles)
  - [request_role](#requestrole)
<!--toc:end-->

# Role Requesting System

This system allows users to request roles, which can then be approved or denied by administrators.

## role_config set_channel

*(Admin Command)*

**Usage:**  
`/role_config set_channel <channel_type> [channel]`  
**Default Values:**  
channel: The channel where the command is used.  
**Permissions:**  
Administrator.  
**Description:**  
Sets the channels for the role request system.  
**Parameter Descriptions:**  
channel_type: The type of channel to set. Choices are "使用者申請頻道" (User Request Channel) and "管理員審核頻道" (Admin Approval Channel).  
channel: The text channel to assign to the selected type. Defaults to the current channel.  

## role_config add_requestable_role

*(Admin Command)*

**Usage:**  
`/role_config add_requestable_role <role>`  
**Default Values:**  
None.  
**Permissions:**  
Administrator.  
**Description:**  
Adds a role to the list of roles that users can request.  
**Parameter Descriptions:**  
role: The role to make requestable.  

## role_config remove_requestable_role

*(Admin Command)*

**Usage:**  
`/role_config remove_requestable_role <role>`  
**Default Values:**  
None.  
**Permissions:**  
Administrator.  
**Description:**  
Removes a role from the list of requestable roles.  
**Parameter Descriptions:**  
role: The role to remove from the requestable list.  

## check_request_status

**Usage:**  
`/check_request_status`  
**Default Values:**  
None.  
**Permissions:**  
None.  
**Description:**  
Checks and displays the current configuration status of the role request system in the server, including set channels and requestable roles.  

## check_requestable_roles

**Usage:**  
`/check_requestable_roles`  
**Default Values:**  
None.  
**Permissions:**  
None.  
**Description:**  
Lists all roles that are currently available for users to request in the server.  

## request_role

**Usage:**  
`/request_role <role> <image> [yt_channel_url]`  
**Default Values:**  
yt_channel_url: None.  
**Permissions:**  
None.  
**Description:**  
Allows a user to request a role. The request is sent to the admin approval channel for review.  
**Parameter Descriptions:**  
role: The role you wish to request.  
image: An image attachment as proof or for verification.  
yt_channel_url: An optional YouTube channel URL, required for specific roles like Youtuber.
