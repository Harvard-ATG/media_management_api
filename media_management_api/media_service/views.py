import logging

from django.db import transaction
from django.db.models import Q
from django.shortcuts import get_object_or_404
from rest_framework import exceptions, status, viewsets
from rest_framework.generics import GenericAPIView
from rest_framework.parsers import FormParser, JSONParser, MultiPartParser
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.reverse import reverse
from rest_framework.views import APIView
from rest_framework_csv.renderers import CSVRenderer

from .filters import IsCourseUserFilterBackend
from .mediastore import processFileUploads, processRemoteImages
from .models import (
    Collection,
    CollectionResource,
    Course,
    CourseCopy,
    CourseUser,
    Resource,
)
from .permissions import IsCourseUserAuthenticated
from .serializers import (
    CollectionResourceSerializer,
    CollectionSerializer,
    CourseCopySerializer,
    CourseSerializer,
    CsvExportResourceSerializer,
    ResourceSerializer,
)

logger = logging.getLogger(__name__)


class APIRoot(APIView):
    def get(self, request, format=None):
        return Response(
            {
                "courses": reverse("api:course-list", request=request, format=format),
                "collections": reverse(
                    "api:collection-list", request=request, format=format
                ),
                "images": reverse("api:image-list", request=request, format=format),
                "iiif": reverse("api:iiif:root", request=request, format=format),
            }
        )


class CourseViewSet(viewsets.ModelViewSet):
    """
    A **course** resource contains a set of *images* which may be grouped into *collections*.

    Courses Endpoints
    ----------------

    - `/courses`  Lists courses
    - `/courses/search?q=title|sis_course_id` Search courses
    - `/courses/{pk}` Course detail
    - `/courses/{pk}/course_copy` Lists a course's copy records
    - `/courses/{pk}/collections` Lists a course's collections
    - `/courses/{pk}/images`  Lists a course's images
    - `/courses/{pk}/library_export` Exports a course's images data to CSV

    Querying the list of courses
    ----------------------------

    The following query parameters can be used to query the list of courses:

    - lti_context_id
    - lti_tool_consumer_instance_guid
    - sis_course_id
    - title

    Examples:

    - `/courses?lti_context_id=<context_id>&lti_tool_consumer_instance_guid=<tool_consumer_instance_guid>`
    - `/courses?sis_course_id=<SIS_ID>`
    - `/courses?title=<TITLE>`

    Note on LTI Attributes:
    -----------------------

    A course associated with an LTI context should have the following attributes:

    - `lti_context_id` Opaque identifier that uniquely identifies tool context (i.e. Canvas Course)
    - `lti_tool_consumer_instance_guid` DNS of the consumer instance that launched the tool

    Together, these two attributes should be enough to uniquely identify the course instance on the target platform and link
    it to a course instance in this repository.
    """

    queryset = Course.objects.prefetch_related(
        "resources", "collections", "collections__resources", "resources__media_store"
    )
    serializer_class = CourseSerializer
    permission_classes = (IsCourseUserAuthenticated,)
    filter_backends = (IsCourseUserFilterBackend,)

    def create(self, request):
        response = super(CourseViewSet, self).create(request)
        if response.status_code == 201:
            self._add_admin_to_course(user=request.user, course_id=response.data["id"])
        return response

    def list(self, request, format=None):
        queryset = self.get_queryset()

        # Filter by LTI context
        if "lti_context_id" in self.request.GET:
            queryset = queryset.filter(
                lti_context_id=self.request.GET["lti_context_id"]
            )
        if "lti_tool_consumer_instance_guid" in self.request.GET:
            queryset = queryset.filter(
                lti_tool_consumer_instance_guid=self.request.GET[
                    "lti_tool_consumer_instance_guid"
                ]
            )

        # Filter by Canvas course ID
        if "canvas_course_id" in self.request.GET:
            queryset = queryset.filter(
                canvas_course_id=self.request.GET["canvas_course_id"]
            )

        # Filter by title or SIS ID
        if "title" in self.request.GET:
            queryset = queryset.filter(title=self.request.GET["title"])
        if "sis_course_id" in self.request.GET:
            queryset = queryset.filter(sis_course_id=self.request.GET["sis_course_id"])

        serializer = self.get_serializer(
            queryset, many=True, context={"request": request}
        )
        return Response(serializer.data)

    def retrieve(self, request, pk=None, format=None):
        course = self.get_object()
        include = ["images", "collections"]
        serializer = self.get_serializer(
            course, context={"request": request}, include=include
        )
        return Response(serializer.data)

    def _add_admin_to_course(self, user=None, course_id=None):
        return CourseUser.add_user_to_course(
            user=user, course_id=course_id, is_admin=True
        )


class CourseSearchView(GenericAPIView):

    """
    Search courses by title or SIS ID.

    Endpoints
    ---------

    - `/courses/search`

    Methods
    -------

    - `GET /courses/search?q=title|sis_course_id`

    """

    queryset = Course.objects.all()
    serializer_class = CourseSerializer
    permission_classes = (IsAuthenticated,)

    def get(self, request, format=None):
        queryset = self.get_queryset()
        if "q" not in self.request.GET:
            return Response([])
        searchtext = self.request.GET["q"]
        queryset = queryset.filter(
            Q(title__startswith=searchtext) | Q(sis_course_id__startswith=searchtext)
        )
        serializer = self.get_serializer(
            queryset, many=True, context={"request": request}
        )
        return Response(serializer.data)


class CourseCopyView(GenericAPIView):
    """
    A **course copy** resource is used tocopy of another course's collections and image resources.

    Endpoints
    ---------

    - `/courses/<pk>/course_copy`

    Methods
    -------

    - `GET /courses/<pk>/course_copy` List record of course copies
    - `POST /courses/<pk>/course_copy` Request a copy of the specified course
    - `DELETE /courses/<pk>/course_copy` Clears copy records

    You must specify `{source_id: "<pk>"}` when submitting a POST request. The value of the `source_id` should be
    the primary key of the course being copied.
    """

    queryset = CourseCopy.objects.all()
    serializer_class = CourseCopySerializer
    permission_classes = (IsCourseUserAuthenticated,)

    def get(self, request, pk, format=None):
        course_pk = pk
        copy_qs = self.get_queryset().filter(dest_id=course_pk)
        if "source_id" in request.GET:
            copy_qs = copy_qs.filter(source_id=request.GET["source_id"])
        if "state" in request.GET:
            copy_qs = copy_qs.filter(state=request.GET["state"])
        serializer = self.get_serializer(
            copy_qs, many=True, context={"request": request}
        )
        return Response(serializer.data)

    def post(self, request, pk, format=None):
        """
        Initiates a copy if one does not already exist for the src/dest combination.
        The assumption is that a course should only be copied once into the target.
        """
        dest_pk = pk

        if "copy_source_id" not in request.data or not request.data["copy_source_id"]:
            raise exceptions.ValidationError(
                "Must provide 'copy_source_id' to identify the course to copy.", 400
            )
        source_id = str(request.data["copy_source_id"])
        if source_id == pk:
            raise exceptions.ValidationError("Cannot copy self", 400)

        # Ensure that both courses exist
        dest_course = get_object_or_404(Course, pk=dest_pk)
        source_course = get_object_or_404(Course, pk=source_id)

        # Check permissions on source and destination courses
        self.check_object_permissions(request, dest_course)
        self.check_object_permissions(request, source_course)

        status = 200
        result = {}
        copy_qs = self.get_queryset().filter(dest=dest_course, source=source_course)
        if copy_qs.exists():
            course_copy = copy_qs[0]
            result["data"] = self.get_serializer(
                course_copy, context={"request": request}
            ).data
            if course_copy.state == CourseCopy.STATE_INITIATED:
                result["message"] = "Copy already initiated"
            elif course_copy.state == CourseCopy.STATE_COMPLETED:
                result["message"] = "Copy already completed"
            elif course_copy.state == CourseCopy.STATE_ERROR:
                result["message"] = "Copy error"
                result["error"] = "An error occurred with the copy process"
                status = 500
            else:
                result["message"] = "Copy state unknown"
                result["error"] = result["message"]
                status = 500
        else:
            course_copy = source_course.copy(dest_course)
            result["message"] = "Copy successful"
            result["data"] = self.get_serializer(
                course_copy, context={"request": request}
            ).data
        return Response(result, status=status)

    def delete(self, request, pk, format=None):
        course_pk = pk
        course = get_object_or_404(Course, pk=course_pk)
        self.check_object_permissions(request, course)

        result = self.get_queryset().filter(dest_id=course_pk).delete()
        num_deleted = result[0]
        msg = "Deleted %s copy records in course %s" % (num_deleted, course_pk)
        logger.info(msg)
        return Response({"message": msg})


class CollectionViewSet(viewsets.ModelViewSet):
    """
    A **collection** resource is a grouping of *images*.

    Endpoints
    ----------------

    - `/collections`
    - `/collections/{pk}`

    Methods
    -------

    - `GET /collections`  Lists collections
    - `POST /collections` Creates new collection
    - `GET /collections/{pk}` Retrieves collection details
    - `PUT /collections/{pk}` Updates collection
    - `DELETE /collections/{pk}` Deletes a collection
    - `GET /collections/{pk}/images`  Lists a collection's images
    """

    queryset = Collection.objects.select_related("course").prefetch_related(
        "resources__resource__media_store"
    )
    serializer_class = CollectionSerializer
    permission_classes = (IsCourseUserAuthenticated,)
    filter_backends = (IsCourseUserFilterBackend,)
    course_user_filter_key = "course__pk__in"

    def get_queryset(self):
        queryset = super(CollectionViewSet, self).get_queryset()
        return self.filter_queryset(queryset)

    def check_object_permissions(self, request, obj):
        super(CollectionViewSet, self).check_object_permissions(request, obj.course)

    def list(self, request, format=None):
        queryset = self.get_queryset()
        serializer = self.get_serializer(
            queryset, many=True, context={"request": request}
        )
        return Response(serializer.data)

    def retrieve(self, request, pk=None, format=None):
        collection = self.get_object()
        serializer = self.get_serializer(
            collection, many=False, context={"request": request}, include=["images"]
        )
        return Response(serializer.data)


class CourseCollectionsView(GenericAPIView):
    """
    A **course collections** resource is a set of *collections* that belong to a *course*.

    Endpoints
    ----------------

    - `/courses/{pk}/collections`

    Methods
    -------

    - `GET /courses/{pk}/collections`  Lists collections that belong to the course
    - `POST /courses/{pk}/collections` Creates a new collection and adds it to the course
    - `PUT /courses/{pk}/collections`  Updates collections
    - `DELETE /courses/{pk}/collections` Deletes collections

    Details
    -------

    ### Updating the order of collections in one batch

    Provide an array of collection IDs:

        PUT /courses/{pk}/collections
        {
                "sort_order": [1,7,6,5,3,2]
        }

    ### Updating the details of collections in one batch

    Provide an array of items, which are just collection objects:

        PUT /courses/{pk}/collections
        {
            "items": [{
                "id": 1,
                "title": "Collection #1",
                "description": "Foo",
                "sort_order": 1
            }, {
                "id": 2,
                "title": "Collection #2",
                "description": "Bar",
                "sort_order": 2
            }]
        }

    """

    queryset = Collection.objects.select_related("course").prefetch_related(
        "resources__resource__media_store"
    )
    serializer_class = CollectionSerializer
    permission_classes = (IsCourseUserAuthenticated,)
    filter_backends = (IsCourseUserFilterBackend,)
    course_user_filter_key = "course__pk__in"

    def get_queryset(self):
        queryset = super(CourseCollectionsView, self).get_queryset()
        return self.filter_queryset(queryset)

    def get(self, request, pk=None, format=None):
        course_pk = pk
        queryset = self.get_queryset()
        queryset = queryset.filter(course__pk=course_pk).order_by("sort_order")
        serializer = self.get_serializer(
            queryset, many=True, context={"request": request}, include=["images"]
        )
        return Response(serializer.data)

    def post(self, request, pk=None, format=None):
        course_pk = pk
        data = request.data
        course = get_object_or_404(Course, pk=course_pk)
        self.check_object_permissions(request, course)

        data["course_id"] = course.pk
        serializer = self.get_serializer(data=data, context={"request": request})
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    def put(self, request, pk=None, format=None):
        course_pk = pk
        course = get_object_or_404(Course, pk=course_pk)
        self.check_object_permissions(request, course)

        if not isinstance(request.data, dict):
            raise exceptions.APIException("Invalid data for course: %s." % course_pk)

        collections = (
            self.get_queryset().filter(course__pk=course_pk).order_by("sort_order")
        )
        collection_ids = [c.pk for c in collections]
        collection_map = dict([(c.pk, c) for c in collections])
        data = request.data

        # Shortcut to just update the order of collections
        if "sort_order" in data:
            if not isinstance(data["sort_order"], list):
                raise exceptions.APIException("Error, key 'sort_order' must be a list")
            elif not (set(collection_ids) == set(data["sort_order"])):
                mismatch = list(set(collection_ids) - set(data["sort_order"]))
                raise exceptions.APIException(
                    "Error updating sort order. Missing or invalid collection IDs. Set mismatch: %s"
                    % mismatch
                )
            with transaction.atomic():
                for index, collection_id in enumerate(data["sort_order"], start=1):
                    collection = collection_map[collection_id]
                    collection.sort_order = index
                    collection.save()
                    logger.debug(
                        "Updated collection=%s sort_order=%s"
                        % (collection.pk, collection.sort_order)
                    )
            return Response(
                {"message": "Sort order updated", "data": data["sort_order"]}
            )

        # Update a batch of collections
        elif "items" in data:
            for item in data["items"]:
                if "id" not in item:
                    raise exceptions.APIException(
                        "Error updating collections. Collection missing collection primary key 'id'. Given: %s"
                        % item
                    )

            item_ids = [item["id"] for item in data["items"]]
            if not (set(item_ids) <= set(collection_ids)):
                raise exceptions.APIException(
                    "Error updating collections. Given collection items MUT be a subset of the course collections."
                )

            logger.debug("Updating collections: %s" % item_ids)
            serializer_data = []
            for item in data["items"]:
                collection_instance = collection_map[item["id"]]
                serializer = self.get_serializer(
                    collection_instance, data=item, context={"request": request}
                )
                serializer.is_valid(raise_exception=True)
                serializer.save()
                serializer_data.append(serializer.data)
            return Response(serializer_data)

        raise exceptions.APIException(
            "Must specify one of 'items' or 'sort_order' to update a batch of collections for course %s."
            % course_pk
        )

    def delete(self, request, pk=None, format=None):
        course_pk = pk
        course = get_object_or_404(Course, pk=course_pk)
        self.check_object_permissions(request, course)
        results = Collection.objects.filter(course_id=course_pk).delete()
        num_deleted = results[0]
        msg = "Deleted %s collections in course %s" % (num_deleted, course_pk)
        logger.info(msg)
        return Response({"message": msg})


class CourseImagesListView(GenericAPIView):
    """
    A **course images** resource is a set of *images* that belong to a *course*.
    This is also referred to as the course's image library.

    Endpoints
    ----------------

    - `/courses/{pk}/images`

    Methods
    -------

    - `GET /courses/{pk}/images`  Lists images that belong to the course
    - `POST /courses/{pk}/images` Uploads an image to the course
    - `DELETE /courses/{pk}/images` Deletes images that belong to the course

    """

    serializer_class = ResourceSerializer
    queryset = Resource.objects.select_related("course", "media_store")
    parser_classes = (JSONParser, MultiPartParser, FormParser)
    permission_classes = (IsCourseUserAuthenticated,)
    filter_backends = (IsCourseUserFilterBackend,)
    course_user_filter_key = "course__pk__in"

    def get_queryset(self):
        queryset = super(CourseImagesListView, self).get_queryset()
        return self.filter_queryset(queryset)

    def get(self, request, pk=None, format=None):
        course_pk = pk
        queryset = self.get_queryset()
        queryset = queryset.filter(course__pk=course_pk).order_by("sort_order")
        serializer = self.get_serializer(
            queryset, many=True, context={"request": request}
        )
        return Response(serializer.data)

    def post(self, request, pk=None, format=None):
        logger.debug(
            "request content_type=%s data=%s" % (request.content_type, request.data)
        )
        request_data = request.data
        course_pk = pk
        course = get_object_or_404(Course, pk=course_pk)
        self.check_object_permissions(request, course)

        request_data["course_id"] = course.pk
        response_data = []
        serializers = []

        # Handle images uploaded directly
        if request.content_type.startswith("multipart/form-data"):
            file_param = "file"
            if file_param not in request.FILES:
                raise exceptions.APIException(
                    "Error: missing '%s' parameter in upload" % file_param
                )
            elif len(request.FILES) == 0:
                raise exceptions.APIException("Error: no files uploaded")
            logger.debug("File uploads: %s" % request.FILES.getlist(file_param))
            processed_uploads = processFileUploads(request.FILES.getlist(file_param))
            for index, f in processed_uploads.items():
                data = request_data
                logger.debug("Processing file upload: %s" % f.name)
                serializer = self.get_serializer(
                    data=data,
                    context={"request": request},
                    is_upload=True,
                    file_object=f,
                )
                serializers.append(serializer)

        # Handle import of images by URL, provided in a JSON message
        elif request.content_type.startswith("application/json"):
            logger.debug("Request data: %s" % request_data)
            MAX_IMAGE_ITEMS = (
                10  # max number of item urls that we will import at a time
            )
            if "items" not in request_data or not isinstance(
                request_data["items"], list
            ):
                raise exceptions.APIException(
                    "Error: missing 'items' parameter for JSON upload"
                )
            elif len(request_data["items"]) == 0:
                raise exceptions.APIException("Error: empty image items")
            elif len(request_data["items"]) > MAX_IMAGE_ITEMS:
                raise exceptions.APIException(
                    "Error: exceeded maximum number of image items (max=%d)."
                    % MAX_IMAGE_ITEMS
                )
            try:
                processed_items = processRemoteImages(request_data["items"])
            except Exception as e:
                raise exceptions.APIException(str(e))

            for url, item in processed_items.items():
                f = item["file"]
                data = item["data"].copy()
                data["course_id"] = course.pk
                logger.debug(
                    "Processing image url=%s file=%s data=%s" % (url, f.name, data)
                )
                serializer = self.get_serializer(
                    data=data,
                    context={"request": request},
                    is_upload=False,
                    file_object=f,
                    file_url=url,
                )
                serializers.append(serializer)
        else:
            raise exceptions.APIException(
                "Error: content type '%s' not supported" % request.content_type
            )

        # Complete the process by serializing the resources
        for serializer in serializers:
            if serializer.is_valid():
                serializer.save()
                response_data.append(serializer.data)
            else:
                logger.error(serializer.errors)
                return Response(
                    response_data + [serializer.errors],
                    status=status.HTTP_400_BAD_REQUEST,
                )
        return Response(response_data, status=status.HTTP_201_CREATED)

    def delete(self, request, pk=None, format=None):
        course_pk = pk
        course = get_object_or_404(Course, pk=course_pk)
        self.check_object_permissions(request, course)

        resources = self.get_queryset().filter(course=course).order_by("sort_order")
        num_deleted = 0
        for resource in resources:
            resource.delete()  # calling manually because the instance delete() contains logic pertaining to the media store
            num_deleted += 1
        msg = "Deleted %s images in course %s" % (num_deleted, course_pk)
        logger.info(msg)
        return Response({"message": msg})


class CourseImagesListCsvExportView(GenericAPIView):
    """
    A **course images** resource is a set of *images* that belong to a *course*.
    This is also referred to as the course's image library.

    Endpoints
    ----------------

    - `/courses/{pk}/library_export`

    Methods
    -------

    - `GET /courses/{pk}/library_export`  Exports images that belong to the course

    """

    serializer_class = CsvExportResourceSerializer
    queryset = Resource.objects.select_related("course", "media_store")
    # there is no browseable api renderer for this view
    # by using CSVRender as the only format, you remove the '?format=csv' query parameters from
    # the url field in the output
    renderer_classes = (CSVRenderer,)
    permission_classes = (IsCourseUserAuthenticated,)
    filter_backends = (IsCourseUserFilterBackend,)
    course_user_filter_key = "course__pk__in"

    def get_queryset(self):
        queryset = super(CourseImagesListCsvExportView, self).get_queryset()
        return self.filter_queryset(queryset)

    def get(self, request, pk=None, format=None):
        course_pk = pk
        queryset = self.get_queryset()
        queryset = queryset.filter(course__pk=course_pk).order_by("sort_order")
        serializer = self.get_serializer(
            queryset, many=True, context={"request": request}
        )
        return Response(serializer.data)


class CollectionImagesListView(GenericAPIView):
    """
    A **collection images** resource is a set of *images* that are associated with a *collection*.

    Endpoints
    ----------------

    - `/collections/{pk}/images`

    Methods
    -------

    - `GET /collections/{pk}/images`  Lists images that belong to the course
    - `POST /collections/{pk}/images` Adds images to the collection that already exist in the course library.
    """

    queryset = CollectionResource.objects.select_related(
        "collection", "resource"
    ).prefetch_related("resource__media_store")
    serializer_class = CollectionResourceSerializer
    permission_classes = (IsCourseUserAuthenticated,)
    filter_backends = (IsCourseUserFilterBackend,)
    course_user_filter_key = "collection__course__pk__in"

    def get_queryset(self):
        queryset = super(CollectionImagesListView, self).get_queryset()
        return self.filter_queryset(queryset)

    def get(self, request, pk=None, format=None):
        queryset = self.get_queryset()
        queryset = queryset.filter(collection__pk=pk).order_by("sort_order")
        serializer = self.get_serializer(
            queryset, many=True, context={"request": request}
        )
        return Response(serializer.data)

    def post(self, request, pk=None, format=None):
        collection = get_object_or_404(Collection, pk=pk)
        self.check_object_permissions(request, collection.course)

        data = []
        for collection_resource in request.data:
            collection_resource = collection_resource.copy()
            collection_resource["collection_id"] = collection.pk
            data.append(collection_resource)
        serializer = self.get_serializer(
            data=data, many=True, context={"request": request}
        )
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class CollectionImagesDetailView(GenericAPIView):
    """
    A **collection images detail** resource describes an image that has been associated with a collection.

    Endpoints
    ----------------

    - `collection-images/{pk}`

    Methods
    -------

    - `GET /collection-images/{pk}` Retrieves details of image associated with collection
    - `DELETE /collection-images/{pk}` Removes the image from the collection
    """

    queryset = CollectionResource.objects.all()
    serializer_class = CollectionResourceSerializer
    permission_classes = (IsCourseUserAuthenticated,)
    filter_backends = (IsCourseUserFilterBackend,)
    course_user_filter_key = "collection__course__pk__in"

    def get_queryset(self):
        queryset = super(CollectionImagesDetailView, self).get_queryset()
        return self.filter_queryset(queryset)

    def check_object_permissions(self, request, obj):
        return super(CollectionImagesDetailView, self).check_object_permissions(
            request, obj.collection.course
        )

    def get(self, request, pk=None, format=None):
        collection_resource = self.get_object()
        serializer = self.get_serializer(
            collection_resource, context={"request": request}
        )
        return Response(serializer.data)

    def delete(self, request, pk=None, format=None):
        collection_resource = self.get_object()
        collection_resource.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)


class CourseImageViewSet(viewsets.ModelViewSet):
    """
    A **course images** resource is a set of *images* that are associated with a *collection*.

    Endpoints
    ----------------

    - `/images`
    - `/images/{pk}`

    Methods
    -------

    - `GET /images`  Lists images
    - `GET /images/{pk}` Retrieves details of an image
    """

    queryset = Resource.objects.select_related("course", "media_store")
    serializer_class = ResourceSerializer
    permission_classes = (IsCourseUserAuthenticated,)
    filter_backends = (IsCourseUserFilterBackend,)
    course_user_filter_key = "course__pk__in"

    def get_queryset(self):
        queryset = super(CourseImageViewSet, self).get_queryset()
        return self.filter_queryset(queryset)

    def check_object_permissions(self, request, obj):
        super(CourseImageViewSet, self).check_object_permissions(request, obj.course)
