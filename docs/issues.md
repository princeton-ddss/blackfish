# Blackfish Issues

## General
- [ ] `blackfish ls` formats images with underscores, while hyphens are used almost everywhere else. This isn't really a CLI issue, but an issue with how image is formatted in the database.

### blackfish init
- [ ] Add option(s) that will allow user to init Blackfish programmatically instead of interactively

### blackfish start
- [x] Change BLACKFISH_DEBUG to support `0/1` value


## Services
- [ ] Create `blackfish service` and alias to `blackfish ls`

### blackfish run, blackfish service run
- [x] Change `text-generate` command to `text-generation`

### blackfish run text-generation
- [x] Make `model` an argument
- [ ] Change `model` to `repo_id`

### blackfish run speech-recognition
- [x] Change `model-id` to `model` (or `repo_id`—whichever used for text generation)
- [x] Make `input_dir` an argument

### blackfish ls, blackfish service ls
- [x] "PORTS" should be "PORT" (i.e., the *local* port)—`details` can list both local and remote ports
- [ ] Format `created_at` and `updated_at` as "5 MIN AGO", etc.
- [ ] Add `id` to the filter options
- [ ] Add `model` to the filter options
- [ ] Add `created_at` and `updated_at` to filter options
- [ ] Add `port` to filter options
- [ ] Add `name` to filter options
- [ ] Add `mounts` to filter options

### blackfish stop, blackfish service stop
- [ ] Add `filters` option to stop multiple services
- [ ] Add `-n,--name` option to stop by name

### blackfish rm, blackfish service rm
- [ ] Add `filters` option to remove multiple services
- [ ] Add `-n,--name` option to remove by name

### blackfish prune, blackfish service prune
- [ ] Create this command. It removes all services that are not running.

### blackfish details, blackfish service details
- [ ] ...

### blackfish fetch, blackfish service fetch
- [ ] The challenge here is to support the options provided by the API. Should there be a single command, or separate commands for each task?blackf


## Models

### blackfish model ls
No issues here.

### blackfish model add
- [ ] Confirm that cancelled/failed downloads are not listed

### blackfish model rm
No issues here.


## Profiles

### blackfish profile ls
No issues here.

### blackfish profile rm
- [ ] Add a `--force` option to bypass confirmation

### blackfish profile add
- [ ] Add options for programmatic adds

### blackfish profile update
- [ ] Add options for programmatic updates

### blackfish profile show
No issues here.


## Images
- [ ] Add support to manage images.


# Blackfish API
- [ ] Async endpoints?
- [ ] `ctrl-c` handling, etc.
- [ ] Review job, service logic for bugs, 

## GET /files
## GET /audio
## GET /ports

## POST /services
## PUT /services/{service_id}/stop
## GET /services/{service_id}
## GET /services
## DEL /services/{service_id}
- [ ] The `endpoints` field isn't populated in Services table. It should contain a list of endpoints that this service provides, e.g., "[{'method': 'POST', 'path': '/generate_stream'}, {'method': 'POST', 'path': '/generate'}]".

## GET /models
## GET /models/{model_id}
## POST /models
## DEL /models/{model_id}
- [ ] Create an endpoint to add a model. The model should be added in a background task. Note: the current `add_model` endpoint just adds a model to the database.
- [ ] Create an endpoint to delete a model. The model should be deleted in a background task. Note: the current `delete_model` endpoint just deletes a model from the database.

## GET /profiles
- [ ] Add POST /profiles
- [ ] Implement PUT /profiles
- [ ] Implement DELETE /profiles/{profile}


# Checklist

- [x] UI
    - [ ] Merge dashboard updates to pilot
- [ ] CLI
- [ ] API
- [ ] "All up" testing
    - [ ] Package UI w/ API
- [ ] Docs
- [ ] Recordings
- [ ] v0.1.0-alpha
