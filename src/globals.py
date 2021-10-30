import os
import supervisely_lib as sly
from diskcache import Cache
from supervisely_lib.io.fs import mkdir

my_app = sly.AppService()

api: sly.Api = my_app.public_api
task_id = my_app.task_id

TEAM_ID = int(os.environ['context.teamId'])
WORKSPACE_ID = int(os.environ['context.workspaceId'])
PROJECT_ID = int(os.environ['modal.state.slyProjectId'])
DATASET_ID = os.environ.get('modal.state.slyDatasetId', None)
if DATASET_ID is not None:
    DATASET_ID = int(DATASET_ID)

project = None
datasets = None

if DATASET_ID is not None:
    dataset_info = api.dataset.get_info_by_id(DATASET_ID)
    datasets = [dataset_info]

project_info = api.project.get_info_by_id(PROJECT_ID)

if datasets is None:
    datasets = api.dataset.get_list(PROJECT_ID)

meta_json = api.project.get_meta(project_info.id)
meta = sly.ProjectMeta.from_json(meta_json)

all_images = []
for dataset in datasets:
    images = api.image.get_list(dataset.id, sort="name")
    all_images.extend(images)

image_ids = [image_info.id for image_info in all_images]
images_urls = [image_info.full_storage_url for image_info in all_images]
images_names = [image_info.name for image_info in all_images]

work_dir = os.path.join(my_app.data_dir, "work_dir")
mkdir(work_dir, True)
cache_dir = os.path.join(work_dir, "diskcache")
mkdir(cache_dir)
cache = Cache(directory=cache_dir)
cache_item_expire_time = 600  # seconds

images_on_page = 3
columns_on_page = len(meta.obj_classes)
first_page = 1
old_input = None
old_rows = None
with_info = True
full_gallery = None
curr_images_ids = None
curr_anns = None

classes_layout_map = {}
# for idx, obj_class in enumerate(meta.obj_classes):
#     classes_layout_map[obj_class.name] = idx + 1
