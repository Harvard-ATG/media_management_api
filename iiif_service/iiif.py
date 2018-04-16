from django.core.urlresolvers import reverse
from django.conf import settings
import json
import urllib

DEBUG = settings.DEBUG

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

    def get_data(self, object_type, object_id):
        if self.manifest is None:
            self.manifest = self.create_manifest()
        if object_type is not None:
            found_object = self.manifest.find_object(object_type, object_id)
            if found_object is not None:
                return found_object.to_dict()
            return None
        return self.manifest.to_dict()

class IIIFObject(object):
    '''
    IIIF Object is the base object for IIIF presentation classes.

    This class contains shared behaviors and methods that should be implemented.

    See also: http://iiif.io/api/presentation/2.0/
    '''
    def url(self):
        '''Returns an absolute URL to the object.'''
        raise Exception("not implemented yet")

    def to_dict(self):
        '''Returns itself as a dictionary.'''
        raise Exception("not implemented yet")

    def to_json(self):
        '''Returns itself as JSON.'''
        obj = self.to_dict()
        if DEBUG:
            return json.dumps(obj, sort_keys=True, indent=4, separators=(',', ': '))
        return json.dumps(obj)

    def __unicode__(self):
        '''Returns a string representation.'''
        return self.to_json()

class IIIFManifest(IIIFObject):
    '''
    IIIFManifest represents a collection of images and defines the overall structure
    of the collection.

    A Manifest object is composed of Sequence, Canvas, and ImageResource objects:

    Manifest
        Sequence
            Canvas
                ImageResource
            Canvas
                ImageResource
            Canvas
                ImageResource

    Each object must have a unique ID that can be mapped to a URL. For this implementation:

        -the Manifest may be uniquely identified by the resource ID.
        -the Sequence may be uniquely identified by "1" because there is only
         one Sequence in this implementation.
        -the Canvas may be uniquely identified by the image ID because
         Canvas:ImageResource is 1:1 in this implementation.
        -the ImageResource may be uniquely identified by the image ID.

    This is intended to be a minimal implementation of the IIIF 2.0 Presentation specification,
    so not all features are supported.

    Usage:

    manifest = Manifest(1)
    manifest.create(images=[
        {'id': 1, 'is_iiif': True, 'url': 'http://localhost:8000/loris/foo.jpg'},
        {'id': 2, 'is_iiif': True, 'url': 'http://localhost:8000/loris/bar.jpg'}
    ])
    output = manifest.to_json()
    print output
    '''
    def __init__(self, request, manifest_id, **kwargs):
        self.request = request
        self.id = manifest_id
        self.label = kwargs.get('label', '')
        self.description = kwargs.get('description', '')
        self.sequences = []
        if 'images' in kwargs:
            self.create(images=kwargs.get('images'))

    def create(self, images=None):
        if images is None:
            images = []
        seq = self.add_sequence(1)
        for n, img in enumerate(images, start=1):
            if img['is_iiif']:
                can = seq.add_canvas(img['id'])
                can.set_label(img['label'])
                can.set_description(img['description'])
                can.set_metadata(img['metadata'])
                can.add_image({
                    'id': img['id'],
                    'url': img['url'],
                    'format': img.get('format', None),
                    'height': img.get('height', None),
                    'width': img.get('width', None),
                    'is_iiif': img.get('is_iiif', True),
                })
        return self

    def add_sequence(self, sequence_id):
        sequence = IIIFSequence(self, sequence_id)
        self.sequences.append(sequence)
        return sequence

    def find_object(self, object_type, object_id):
        import logging
        logging.debug("object_type=%s object_id=%s" % (object_type, object_id))
        if object_type == "manifest":
            if object_id == self.id:
                return self
        elif object_type == "sequence":
            for s in self.sequences:
                if object_id == s.id:
                    return s
        elif object_type in ("canvas", "annotation"):
            for c in self.sequences[0].canvases:
                if object_id == c.id:
                    return c
        elif object_type == "resource":
            for c in self.sequences[0].canvases:
                if object_id == c.resource.id:
                    return c.resource
        return None

    def build_absolute_url(self, route, route_args=None):
        if route_args is None:
            route_args = {}
        route_args['manifest_id'] = self.id
        return self.request.build_absolute_uri(reverse(route, kwargs=route_args))
        
    def url(self):
        return self.build_absolute_url('iiif:manifest')

    def to_dict(self):
        manifest = {
            "@context": "http://iiif.io/api/presentation/2/context.json",
            "@type": "sc:Manifest",
            "@id": self.url(),
            "label": self.label,
            "description": self.description,
            "sequences": [sequence.to_dict() for sequence in self.sequences]
        }
        return manifest

class IIIFSequence(IIIFObject):
    def __init__(self, manifest, sequence_id):
        self.manifest = manifest
        self.id = str(sequence_id)
        self.canvases = []

    def add_canvas(self, canvas_id):
        # Mirador relies on every canvas having a unique URI, so in case we have duplicate image
        # objects in the manifest (i.e. duplicate canvases), we'll add an index to each canvas_id
        # to ensure uniqueness within the manifest.
        index = len(self.canvases)
        canvas_id = "%s.%s" % (canvas_id, index)
        canvas = IIIFCanvas(self.manifest, canvas_id)
        self.canvases.append(canvas)
        return canvas

    def url(self):
        return self.manifest.build_absolute_url('iiif:sequence', {
            'object_type': 'sequence',
            'object_id': self.id
        })

    def to_dict(self):
        sequence = {
            "@id": self.url(),
            "@type": "sc:Sequence",
            "label": "Default order",
            "canvases": [canvas.to_dict() for canvas in self.canvases],
        }
        return sequence

class IIIFCanvas(IIIFObject):
    def __init__(self, manifest, canvas_id):
        self.manifest = manifest
        self.id = canvas_id
        self.label = 'Image'
        self.description = ''
        self.metadata = []
        self.width = 100 # TODO: get real width
        self.height = 100 # TODO: get real height
        self.resource = None

    def add_image(self, image):
        self.resource = IIIFImageResource(self.manifest, self.id, image)
        if image['width'] is not None:
            self.width = image['width']
        if image['height'] is not None:
            self.height = image['height']
        return self

    def set_label(self, label):
        self.label = label

    def set_description(self, description):
        self.description = description

    def set_metadata(self, metadata):
        self.metadata = metadata

    def url(self):
        return self.manifest.build_absolute_url('iiif:canvas', {
            'object_type': 'canvas',
            'object_id': self.id
        })

    def to_dict(self):
        canvas = {
            "@id": self.url(),
            "@type": "sc:Canvas",
            "label": self.label,
            "images": [{
                "@id": self.manifest.build_absolute_url('iiif:annotation', {
                    'object_type': 'annotation',
                    'object_id': self.id
                }),
                "@type": "oa:Annotation",
                "motivation": "sc:painting",
                "resource": self.resource.to_dict(),
                "on": self.url(),
            }],
        }
        if self.description:
            canvas['description'] = self.description
        if self.metadata:
            canvas['metadata'] = self.metadata
        if self.width is not None and self.height is not None:
            canvas['width'] = self.width
            canvas['height'] = self.height
        return canvas

class IIIFImageResource(IIIFObject):
    def __init__(self, manifest, resource_id, image):
        self.manifest = manifest
        self.id = resource_id
        self.image_url = image['url']
        self.format = image.get('format', None)
        self.is_iiif = image.get('is_iiif', False)
        self.width = image.get('width', None)
        self.height = image.get('height', None)

    def url(self):
        return self.manifest.build_absolute_url('iiif:resource', {
            'object_type': 'resource',
            'object_id': self.id
        })

    def to_dict(self):
        if not self.is_iiif:
            resource = {
                "@id": self.image_url,
                "@type": "dctypes:Image",
            }
        else:
            iiif_url_params = dict(base_url=self.image_url, region='full', size='full', rotation=0)
            max_size = 1024
            if self.width is not None and self.width > max_size:
                iiif_url_params['size'] = str(max_size) + ','

            resource = {
                "@id": '{base_url}/{region}/{size}/{rotation}/default.jpg'.format(**iiif_url_params),
                "@type": "dctypes:Image",
                "service": {
                    "@id": self.image_url,
                    "profile": "http://iiif.io/api/image/2/level1.json",
                }
            }
        if self.format:
            resource['format'] = self.format
        if self.width and self.height:
            resource['width'] = self.width
            resource['height'] = self.height
        return resource
