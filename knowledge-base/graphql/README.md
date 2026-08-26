# ESO Logs GraphQL Knowledge Base

Last refreshed: 2026-08-23 19:19:12 -0400
Endpoint: https://www.esologs.com/api/v2/client
Token source: config.local.js client credentials

## Schema Overview

- Query root type: Query
- Mutation root type: none
- Subscription root type: none
- Total types: 102
- OBJECT types: 75
- INPUT_OBJECT types: 2
- ENUM types: 20
- SCALAR types: 5
- INTERFACE types: 0
- UNION types: 0
- Directives: 5

## Root Query Fields

- characterData: Obtain the character data object that allows the retrieval of individual characters or filtered collections of characters.
- gameData: Obtain the game data object that holds collections of static data such as abilities, achievements, classes, items, NPCs, etc..
- guildData: Obtain the guild data object that allows the retrieval of individual guilds or filtered collections of guilds.
- progressRaceData: Obtain information about an ongoing world first or realm first race. Inactive when no race is occurring. This data only updates once every 30 seconds, so you do not need to fetch this information more often than that.
- rateLimitData: Obtain the rate limit data object to see how many points have been spent by this key.
- reportData: Obtain the report data object that allows the retrieval of individual reports or filtered collections of reports by guild or by user.
- userData: Obtain the user object that allows the retrieval of the authorized user's id and username.
- worldData: Obtain the world data object that holds collections of data such as all expansions, regions, subregions, servers, dungeon/raid zones, and encounters.
- reportComponentData: No description available.
- systemReportComponentData: No description available.

## Core Domain Type Snapshots

### ReportData
- Description: The ReportData object enables the retrieval of single reports or filtered collections of reports.
- Fields:
  - report (args: code, allowUnlisted): Obtain a specific report by its code.
  - reports (args: endTime, guildID, guildName, guildServerSlug, guildServerRegion, guildTagID, userID, limit, page, startTime, zoneID, gameZoneID): A set of reports for a specific guild, guild tag, or user.

### CharacterData
- Description: The CharacterData object enables the retrieval of single characters or filtered collections of characters.
- Fields:
  - character (args: id, name, serverSlug, serverRegion): Obtain a specific character either by id or by name/server_slug/server_region.
  - characters (args: guildID, limit, page): A collection of characters for a specific guild.

### GuildData
- Description: The GuildData object enables the retrieval of single guilds or filtered collections of guilds.
- Fields:
  - guild (args: id, name, serverSlug, serverRegion): Obtain a specific guild either by id or by name/serverSlug/serverRegion.
  - guilds (args: limit, page, serverID, serverSlug, serverRegion): The set of all guilds supported by the site. Can be optionally filtered to a specific server id.

### WorldData
- Description: The world data object contains collections of data such as expansions, zones, encounters, regions, subregions, etc.
- Fields:
  - encounter (args: id): Obtain a specific encounter by id.
  - expansion (args: id): A single expansion obtained by ID.
  - expansions (args: none): The set of all expansions supported by the site.
  - region (args: id): Obtain a specific region by its ID.
  - regions (args: none): The set of all regions supported by the site.
  - server (args: id, region, slug): Obtain a specific server either by id or by slug and region.
  - subregion (args: id): Obtain a specific subregion by its ID.
  - zone (args: id): Obtain a specific zone by its ID.
  - zones (args: expansion_id): Obtain a set of all zones supported by the site.

### RateLimitData
- Description: A way to obtain your current rate limit usage.
- Fields:
  - limitPerHour (args: none): The total amount of points this API key can spend per hour.
  - pointsSpentThisHour (args: none): The total amount of points spent during this hour.
  - pointsResetIn (args: none): The number of seconds remaining until the points reset.

### UserData
- Description: The user data object contains basic information about users and lets you retrieve specific users (or the current user if using the user endpoint).
- Fields:
  - user (args: id): Obtain a specific user by id.
  - currentUser (args: none): Obtain the current user (only works with user endpoint).

## Source Artifacts

- introspection-full.json: Full schema introspection result.
- root-schema-summary.json: Query root and directives summary.
- core-types-summary.json: Focused summary of key top-level data objects.
