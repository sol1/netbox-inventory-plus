from utilities.testing import APIViewTestCases

from ...models import Delivery, Purchase, Supplier
from ..custom import APITestCase


class DeliveryTest(
    APITestCase,
    APIViewTestCases.GetObjectViewTestCase,
    APIViewTestCases.ListObjectsViewTestCase,
    APIViewTestCases.CreateObjectViewTestCase,
    APIViewTestCases.UpdateObjectViewTestCase,
    APIViewTestCases.DeleteObjectViewTestCase,
):
    model = Delivery
    brief_fields = ['date', 'description', 'display', 'id', 'name', 'url']

    bulk_update_data = {
        'description': 'new description',
    }

    @classmethod
    def setUpTestData(cls) -> None:
        supplier1 = Supplier.objects.create(name='Supplier1', slug='supplier1')
        purchase1 = Purchase.objects.create(
            name='Purchase1', supplier=supplier1, status='closed'
        )
        delivery1 = Delivery.objects.create(name='Delivery 1')
        delivery1.purchases.set([purchase1])
        delivery2 = Delivery.objects.create(name='Delivery 2')
        delivery2.purchases.set([purchase1])
        delivery3 = Delivery.objects.create(name='Delivery 3')
        delivery3.purchases.set([purchase1])
        cls.create_data = [
            {
                'name': 'Delivery 4',
                'purchases': [purchase1.pk],
            },
            {
                'name': 'Delivery 5',
                'purchases': [purchase1.pk],
            },
            {
                'name': 'Delivery 6',
                'purchases': [purchase1.pk],
            },
        ]
