import supervisely_lib as sly
import functools, os
import globals as g
from create_gallery import Gallery
from supervisely_lib.io.fs import silent_remove, get_file_name
from supervisely_lib.io.json import dump_json_file
from collections import defaultdict


def send_error_data(func):
    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        value = None
        try:
            value = func(*args, **kwargs)
        except Exception as e:
            request_id = kwargs["context"]["request_id"]
            g.my_app.send_response(request_id, data={"error": repr(e)})
        return value

    return wrapper


def get_ann_by_id(id, save_path):
    if g.cache.get(id) is None:
        ann_info = g.api.annotation.download(id)
        ann_json = ann_info.annotation
        ann_json_name = get_file_name(ann_info.image_name) + '.json'
        ann_json_path = os.path.join(save_path, ann_json_name)
        dump_json_file(ann_json, ann_json_path)
        g.cache.add(id, ann_json, expire=g.cache_item_expire_time)
        silent_remove(ann_json_path)
    else:
        ann_json = g.cache.get(id)

    ann = sly.Annotation.from_json(ann_json, g.meta)

    return ann


def update_gallery_by_page(current_page, state):

    images_per_page = state['rows']
    max_pages_count = len(g.image_ids) // images_per_page
    if len(g.image_ids) % images_per_page != 0:
        max_pages_count += 1

    g.full_gallery = Gallery(g.task_id, g.api, 'data.perClass', g.meta, g.columns_on_page)

    curr_images_names = g.images_names[images_per_page * (current_page - 1):images_per_page * current_page]
    curr_images_urls = g.images_urls[images_per_page * (current_page - 1):images_per_page * current_page]

    g.curr_images_ids = g.image_ids[images_per_page * (current_page - 1):images_per_page * current_page]
    g.curr_anns = [get_ann_by_id(image_id, g.cache_dir) for image_id in g.curr_images_ids]

    objects_counter = defaultdict(int)

    for idx, (image_name, ann, image_url) in enumerate(zip(curr_images_names, g.curr_anns, curr_images_urls)):
        # if idx == images_per_page:
        #     break
        for label in ann.labels:
            obj_class_id = g.classes_layout_map[label.obj_class.name]
            objects_counter[label.obj_class.name] += 1
            curr_title = image_name + '_' + label.obj_class.name + '_' + str(objects_counter[label.obj_class.name])
            g.full_gallery.add_item(title=curr_title, ann=ann, image_url=image_url, col_index=obj_class_id)

    g.full_gallery.update(need_zoom=True)

    fields = [
        {"field": "state.galleryPage", "payload": current_page},
        {"field": "state.galleryMaxPage", "payload": max_pages_count},
        {"field": "state.input", "payload": current_page},
        {"field": "state.maxImages", "payload": len(g.image_ids)},
        {"field": "state.rows", "payload": images_per_page},
        {"field": "state.cols", "payload": g.columns_on_page},
        {"field": "state.with_info", "payload": g.with_info}
    ]
    g.api.app.set_fields(g.task_id, fields)


@g.my_app.callback("test_compary_gallery")
@sly.timeit
@send_error_data
def test_compary_gallery(api: sly.Api, task_id, context, state, app_logger):
    g.old_input = state['galleryPage']
    go_to_page = state.get('input')
    if go_to_page is not None:
        current_page = int(go_to_page)
    else:
        current_page = state['galleryPage']

    update_gallery_by_page(current_page, state)


@g.my_app.callback("update_page")
@sly.timeit
@send_error_data
def update_page(api: sly.Api, task_id, context, state, app_logger):
    g.old_input = state['galleryPage']
    go_to_page = state.get('input')
    current_page = int(go_to_page)
    if g.old_input > current_page and g.old_rows != state['rows']:
        current_page = g.first_page
    g.old_rows = state['rows']
    update_gallery_by_page(current_page, state)


def main():
    sly.logger.info("Script arguments", extra={
        "context.teamId": g.TEAM_ID
    })

    state = {'galleryPage': g.first_page, 'rows': g.images_on_page, 'cols': g.columns_on_page}
    data = {'perClass':None}

    g.my_app.run(state=state, data=data, initial_events=[{"state": state, "command": "test_compary_gallery"}])


if __name__ == "__main__":
    sly.main_wrapper("main", main)
