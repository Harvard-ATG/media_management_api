import requests
from objects import IIIFManifest
from rest_framework.exceptions import APIException

class CollectionManifestController(object):
    '''
    This class is responsible for generating a manifest for a given collection object.
    '''
    def __init__(self, request, collection):
        self.request = request
        self.collection = collection
        self.manifest = None

    def get_images(self):
        images = []
        collection_resources = self.collection.resources.all()
        for collection_resource in collection_resources:
            resource = collection_resource.resource
            data = resource.get_representation()
            metadata = resource.load_metadata()
            url = data['iiif_base_url']
            width = data['image_width']
            height = data['image_height']
            image_type = data['image_type']
            images.append({
                "id": resource.id,
                "label": resource.title,
                "description": resource.description,
                "metadata": metadata,
                "is_iiif": resource.media_store is not None,
                "width": width,
                "height": height,
                "url": url,
                "format": image_type,
            })
        return images

    def create_manifest(self):
        images = self.get_images()
        manifest_kwargs = {
            "label": self.collection.title,
            "description": self.collection.description,
            "images": images,
        }
        manifest = IIIFManifest(self.request, self.collection.pk, **manifest_kwargs)
        return manifest

    def fetch_manifest(self, url):
        r = requests.get(url)
        errmsg = 'Failed to load manifest: %s' % url
        if r.status_code != 200:
            raise APIException(code=r.status_code, detail=errmsg)
        if r.headers['content-type'].startswith('application/json'):
            raise APIException(detail=errmsg)
        return r.json()

    def load(self, object_type=None, object_id=None):
        if self.manifest is None:
            self.manifest = self.create_manifest()
        if object_type is not None:
            found_object = self.manifest.find_object(object_type, object_id)
            if found_object is not None:
                return found_object.to_dict()
            return None
        return self.manifest.to_dict()