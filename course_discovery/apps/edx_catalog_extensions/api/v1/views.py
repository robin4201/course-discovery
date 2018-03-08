from course_discovery.apps.api.v1.views.search import AggregateSearchViewSet
from course_discovery.apps.edx_catalog_extensions.api.serializers import DistinctCountsAggregateFacetSearchSerializer
from course_discovery.apps.edx_haystack_extensions.distinct_counts.query import DistinctCountsSearchQuerySet
from functools import lru_cache


class DistinctCountsAggregateSearchViewSet(AggregateSearchViewSet):
    """ Provides a facets action that can include distinct hit and facet counts in the response."""

    # Custom serializer that includes distinct hit and facet counts.
    facet_serializer_class = DistinctCountsAggregateFacetSearchSerializer

    @lru_cache(maxsize=None)
    def get_queryset(self, *args, **kwargs):  # pylint: disable=arguments-differ
        """ Return the base Queryset to use to build up the search query."""
        queryset = super(DistinctCountsAggregateSearchViewSet, self).get_queryset(*args, **kwargs)
        return DistinctCountsSearchQuerySet.from_queryset(queryset).with_distinct_counts('aggregation_key')
