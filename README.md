# Hello!

This is PrimeBDS, an essentials plugin for diagnostics, stability, and quality of life on Minecraft Bedrock Edition.

This plugin is packed with various commands that build on BDS while retaining vanilla functionality. There are many optional settings that can be used for a wide variety of servers. A few systems include:
- A punishment system that includes timed, bans, mutes, and logs
- Numerous bug fixes
- Anti-Crasher
- Discord logging
- Vanilla command aliases
- Diagnostic tools to look at server performance & script performance
- An allowlist profile system
- A combat editor

More features will be released in batches alongside large game updates due to my busy schedule. Feel free to make an issue to suggest new ideas!
I currently have on the docket:
- A way to connect scoreboards to the combat edit system
- A better /transfer command
- A way to start & stop the script profiler / likely will be merged with the /viewscriptprofiles command
- OP list command
- General performance improvements

# NOTICE
- If you are arriving from WMCTCORE, this version relocates database files to one folder inside bedrock_server/plugins. Please rename your wmctcore_users.db to users.db and your wmctcore_gl.db to grieflog.db. Then move these files to the new folder location bedrock_server/plugins/primebds_data 
  - This change was made to keep everything in one place and for future updates to automate changes like these. I hope to avoid such breaking changes in the future.
