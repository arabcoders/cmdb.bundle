# Custom DB matcher for Plex.

This is a agent for [Plex Media Server](https://plex.tv) that purely here to generate unique custom IDs for TV series. to work with 
my other two plugins for [Jellyfin](https://github.com/arabcoders/jf-custom-metadata-db) and [Emby](https://github.com/arabcoders/emby-custom-metadata-db).

**This plugin require server that respond with a unique ID for a given TV series name in the following format.**

```json5
[
    {
        "id": "jp-bded21fb4b",
        "title": "Show Real title",
        "match": [
            "Matchers"
        ]
    },
    ...
]
```

# Server implementation

You can see a quick implementation of the server in [index.php](https://github.com/arabcoders/cmdb.bundle/blob/master/server/index.php) file, i stress this not a production ready server, it's just a quick implementation to get you started to see how the plugins interact with it.

You can use this server as a starting point to build your own server, or you can use any other server that respond with the same format.
This server implementation works for all the plugins custom metadata plugins.

These plugins are purely here to generate unique IDs for TV series, so they can work with [arabcoders/watchstate](https://github.com/arabcoders/watchstate) If you are looking to generate custom metadata for your TV series, you can use the the [NFO plugins](https://github.com/gboudreau/XBMCnfoTVImporter.bundle) for that. I do so myself.

# Installation

In order to use this bundle you **MUST** to use the [jp_scanner.py](https://github.com/arabcoders/plex-daily-scanner). Check the link for installation instructions.

1. Go to the release page and download latest version.
2. Unzip the file and rename the main directory to be `cmdb.bundle` Make sure the `Contents` directory is directly underneath `cmdb.bundle`. 
3. Move the folder into the `Plug-ins` directory in your Plex Media Server installation ([Wait where?](https://support.plex.tv/articles/201106098-how-do-i-find-the-plug-ins-folder/))
4. Create a new library and select "TV Show"
5. Click on the "Advanced" tab and select
    1. Scanner: `jp_scanner`.
    2. Agent: `Custom metadata DB Agent`.
    3. URL for API endpoint: `The url for the server you created`.

Now you are done. At first Plex will scan for all the files, when this is done the agent will attempt to find the metadata associated with the series.