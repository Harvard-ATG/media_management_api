from django.shortcuts import get_object_or_404
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.reverse import reverse
from rest_framework.exceptions import PermissionDenied

from media_management_api.media_service.models import Course, Collection
from .objects import IIIFManifest

class IiifView(APIView):
    def get(self, request, format=None):
        return Response({
            'collections': reverse('api:iiif:collections', request=request, format=format),
        })

class IiifManifestView(APIView):
    def get(self, request, manifest_id=None, object_type=None, object_id=None, format=None):
        collection = get_object_or_404(Collection, pk=manifest_id)

        images = []
        for collection_resource in collection.resources.all():
            resource = collection_resource.resource
            data = resource.get_representation()
            images.append({
                "id": resource.id,
                "label": resource.title,
                "description": resource.description,
                "metadata": resource.load_metadata(),
                "is_iiif": resource.media_store is not None,
                "width": data['image_width'],
                "height": data['image_height'],
                "url": data['iiif_base_url'],
                "format": data['image_type'],
            })

        data = None
        manifest = IIIFManifest(self.request, collection.pk, label=collection.title, description=collection.description, images=images)
        if object_type is not None:
            manifest_res = manifest.find_object(object_type, object_id)
            if manifest_res is not None:
                data = manifest_res.to_dict()
        if data is None:
            data = manifest.to_dict()

        return Response(data)

class IiifCollectionsView(APIView):
    def get(self, request, format=None):
        if not request.user.is_superuser:
            raise PermissionDenied('You do not have permission to view all collections')

        courses = Course.objects.all()
        data = {
            '@context': 'http://iiif.io/api/presentation/2/context.json',
            '@type': 'sc:Collection',
            '@id': request.build_absolute_uri(reverse('api:iiif:collections')),
            'label': 'Top-level collection',
            'members': []
        }
        for c in courses:
            data['members'].append({
                '@type': 'sc:Collection',
                '@id': request.build_absolute_uri(reverse('api:iiif:collection', kwargs={"pk": c.pk})),
                'label': c.title,
            })

        return Response(data)

class IiifCollectionView(APIView):
    def get(self, request, pk=None, format=None):
        course = get_object_or_404(Course, pk=pk)
        data = {
            '@context': 'http://iiif.io/api/presentation/2/context.json',
            '@type': 'sc:Collection',
            '@id': request.build_absolute_uri(reverse('api:iiif:collection', kwargs={"pk": pk})),
            'label': 'Top-level collection: %s' % course.title,
            'members': []
        }
        for c in course.collections.all():
            data['members'].append({
                '@type': 'sc:Manifest',
                '@id': request.build_absolute_uri(reverse('api:iiif:manifest', kwargs={"manifest_id": c.pk})),
                'label': c.title,
            })
        return Response(data)