from django.shortcuts import get_object_or_404
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.reverse import reverse
from rest_framework.exceptions import PermissionDenied

from media_service.models import Course, Collection
import iiif

class IiifAPIRoot(APIView):
    def get(self, request, format=None):
        return Response({
            'collections': reverse('iiif:collections', request=request, format=format),
        })

class IiifManifestView(APIView):
    def get(self, request, manifest_id=None, object_type=None, object_id=None, format=None):
        collection = get_object_or_404(Collection, pk=manifest_id)
        collection_manifest_controller = iiif.CollectionManifestController(request, collection)
        data = collection_manifest_controller.get_data(object_type, object_id)
        return Response(data)

class IiifCollectionsView(APIView):
    def get(self, request, format=None):
        if not request.user.is_superuser:
            raise PermissionDenied('You must have elevated privileges to view all collections')

        courses = Course.objects.all()
        data = {
            '@context': 'http://iiif.io/api/presentation/2/context.json',
            '@type': 'sc:Collection',
            '@id': request.build_absolute_uri(reverse('iiif:collections')),
            'label': 'Top-level collection',
            'members': []
        }
        for c in courses:
            data['members'].append({
                '@type': 'sc:Collection',
                '@id': request.build_absolute_uri(reverse('iiif:collection', kwargs={"pk": c.pk})),
                'label': c.title,
            })

        return Response(data)

class IiifCollectionView(APIView):
    def get(self, request, pk=None, format=None):
        course = get_object_or_404(Course, pk=pk)
        data = {
            '@context': 'http://iiif.io/api/presentation/2/context.json',
            '@type': 'sc:Collection',
            '@id': request.build_absolute_uri(reverse('iiif:collection', kwargs={"pk": pk})),
            'label': 'Top-level collection: %s' % course.title,
            'members': []
        }
        for c in course.collections.all():
            data['members'].append({
                '@type': 'sc:Manifest',
                '@id': request.build_absolute_uri(reverse('iiif:manifest', kwargs={"manifest_id": c.pk})),
                'label': c.title,
            })
        return Response(data)