from django.apps.registry import Apps
from django.db import migrations
from django.db.backends.base.schema import BaseDatabaseSchemaEditor


def remove(apps: Apps, schema_editor: BaseDatabaseSchemaEditor) -> None:
    apps.get_model("providers", "Integration").objects.filter(key="upcitemdb").delete()


class Migration(migrations.Migration):
    dependencies = [("providers", "0001_integrations")]

    operations = [migrations.RunPython(remove, migrations.RunPython.noop)]
