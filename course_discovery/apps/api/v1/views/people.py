import logging

import waffle
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework import status, viewsets
from rest_framework.permissions import DjangoModelPermissions
from rest_framework.response import Response

from course_discovery.apps.api import filters, serializers
from course_discovery.apps.api.pagination import PageNumberPagination
from course_discovery.apps.course_metadata.exceptions import MarketingSiteAPIClientException, PersonToMarketingException
from course_discovery.apps.course_metadata.people import MarketingSitePeople

logger = logging.getLogger(__name__)


# pylint: disable=no-member
class PersonViewSet(viewsets.ModelViewSet):
    """ PersonSerializer resource. """

    filter_backends = (DjangoFilterBackend,)
    filter_class = filters.PersonFilter
    lookup_field = 'uuid'
    lookup_value_regex = '[0-9a-f-]+'
    permission_classes = (DjangoModelPermissions,)
    queryset = serializers.PersonSerializer.prefetch_queryset()
    serializer_class = serializers.PersonSerializer
    pagination_class = PageNumberPagination

    def create(self, request, *args, **kwargs):
        """
        Create a person in discovery and also create a person node in drupal
        """
        person_data = request.data

        partner = request.site.partner
        person_data['partner'] = partner.id
        serializer = self.get_serializer(data=person_data)
        serializer.is_valid(raise_exception=True)

        if not waffle.switch_is_active('publish_person_to_marketing_site'):
            return Response('publish_person_to_marketing_site is disabled.', status=status.HTTP_400_BAD_REQUEST)
        try:
            marketing_person = MarketingSitePeople()
            response = marketing_person.publish_person(
                partner,
                self._get_person_data(serializer)
            )
            serializer.validated_data.pop('uuid')
            serializer.validated_data['uuid'] = response['uuid']

        except (PersonToMarketingException, MarketingSiteAPIClientException):
            logger.exception(
                'An error occurred while adding the person [%s]-[%s] to the marketing site.',
                serializer.validated_data['given_name'], serializer.validated_data['family_name']
            )
            return Response('Failed to add person data to the marketing site.', status=status.HTTP_400_BAD_REQUEST)

        try:
            self.perform_create(serializer)
        except Exception:  # pylint: disable=broad-except
            logger.exception(
                'An error occurred while adding the person [%s]-[%s]-[%s] in discovery.',
                serializer.validated_data['given_name'], serializer.validated_data['family_name'],
                response['id']
            )
            marketing_person.delete_person(partner, response['id'])
            return Response('Failed to add person data.', status=status.HTTP_400_BAD_REQUEST)

        headers = self.get_success_headers(serializer.data)
        return Response(serializer.data, status=status.HTTP_201_CREATED, headers=headers)

    def update(self, request, *args, **kwargs):  # pylint: disable=unused-argument
        """
        Updates a person in discovery and the corresponding person node in drupal
        """
        person_data = request.data

        partner = request.site.partner
        person_data['partner'] = partner.id
        partial = kwargs.pop('partial', False)
        instance = self.get_object()
        serializer = self.get_serializer(instance, data=person_data, partial=partial)
        serializer.is_valid(raise_exception=True)

        if not waffle.switch_is_active('publish_person_to_marketing_site'):
            return Response('publish_person_to_marketing_site is disabled.', status=status.HTTP_400_BAD_REQUEST)
        try:
            marketing_person = MarketingSitePeople()
            marketing_person.update_person(
                partner,
                serializer.validated_data['uuid'],
                self._get_person_data(serializer)
            )

        except (PersonToMarketingException, MarketingSiteAPIClientException):
            logger.exception(
                'An error occurred while updating the person [%s]-[%s] on the marketing site.',
                serializer.validated_data['given_name'], serializer.validated_data['family_name']
            )
            return Response(
                'Failed to update person data on the marketing site.',
                status=status.HTTP_400_BAD_REQUEST
            )

        try:
            self.perform_update(serializer)
        except Exception:  # pylint: disable=broad-except
            logger.exception(
                'An error occurred while updating the person [%s]-[%s] in discovery.',
                serializer.validated_data['given_name'], serializer.validated_data['family_name']
            )
            return Response('Failed to update person data.', status=status.HTTP_400_BAD_REQUEST)

        headers = self.get_success_headers(serializer.data)
        return Response(serializer.data, status=status.HTTP_200_OK, headers=headers)

    def _get_person_data(self, serializer):
        return {
            'given_name': serializer.validated_data['given_name'],
            'family_name': serializer.validated_data['family_name']
        }

    def list(self, request, *args, **kwargs):
        """ Retrieve a list of all people. """
        return super(PersonViewSet, self).list(request, *args, **kwargs)

    def retrieve(self, request, *args, **kwargs):
        """ Retrieve details for a person. """
        return super(PersonViewSet, self).retrieve(request, *args, **kwargs)
