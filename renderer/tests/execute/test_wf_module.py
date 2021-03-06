import contextlib
import logging
import textwrap
from unittest.mock import patch
from django.utils import timezone
from cjwkernel.chroot import EDITABLE_CHROOT
from cjwkernel.types import I18nMessage, RenderError, RenderResult, Tab
from cjwkernel.tests.util import arrow_table, parquet_file
from cjwstate import minio, rabbitmq, rendercache
from cjwstate.storedobjects import create_stored_object
from cjwstate.models import Workflow
from cjwstate.tests.utils import DbTestCaseWithModuleRegistry, create_module_zipfile
from renderer import notifications
from renderer.execute.wf_module import execute_wfmodule


async def noop(*args, **kwargs):
    return


class WfModuleTests(DbTestCaseWithModuleRegistry):
    def setUp(self):
        super().setUp()
        self.ctx = contextlib.ExitStack()
        self.chroot_context = self.ctx.enter_context(EDITABLE_CHROOT.acquire_context())
        basedir = self.ctx.enter_context(
            self.chroot_context.tempdir_context(prefix="test_wf_module-")
        )
        self.output_path = self.ctx.enter_context(
            self.chroot_context.tempfile_context(prefix="output-", dir=basedir)
        )

    def tearDown(self):
        self.ctx.close()
        super().tearDown()

    @patch.object(rabbitmq, "send_update_to_workflow_clients", noop)
    def test_deleted_module(self):
        workflow = Workflow.create_and_init()
        tab = workflow.tabs.first()
        wf_module = tab.wf_modules.create(
            order=0,
            slug="step-1",
            module_id_name="deleted_module",
            last_relevant_delta_id=workflow.last_delta_id,
        )
        result = self.run_with_async_db(
            execute_wfmodule(
                self.chroot_context,
                workflow,
                wf_module,
                None,
                {},
                tab.to_arrow(),
                RenderResult(),
                {},
                self.output_path,
            )
        )
        expected = RenderResult(
            errors=[RenderError(I18nMessage("py.renderer.execute.wf_module.noModule"))]
        )
        self.assertEqual(result, expected)
        wf_module.refresh_from_db()
        self.assertEqual(wf_module.cached_render_result.errors, expected.errors)

    @patch.object(rabbitmq, "send_update_to_workflow_clients", noop)
    @patch.object(notifications, "email_output_delta")
    def test_email_delta(self, email_delta):
        workflow = Workflow.create_and_init()
        tab = workflow.tabs.first()
        wf_module = tab.wf_modules.create(
            order=0,
            slug="step-1",
            module_id_name="x",
            last_relevant_delta_id=workflow.last_delta_id - 1,
            notifications=True,
        )
        rendercache.cache_render_result(
            workflow,
            wf_module,
            workflow.last_delta_id - 1,
            RenderResult(arrow_table({"A": [1]})),
        )
        wf_module.last_relevant_delta_id = workflow.last_delta_id
        wf_module.save(update_fields=["last_relevant_delta_id"])

        module_zipfile = create_module_zipfile(
            "x",
            python_code='import pandas as pd\ndef render(table, params): return pd.DataFrame({"A": [2]})',
        )
        with self.assertLogs(level=logging.INFO):
            self.run_with_async_db(
                execute_wfmodule(
                    self.chroot_context,
                    workflow,
                    wf_module,
                    module_zipfile,
                    {},
                    Tab(tab.slug, tab.name),
                    RenderResult(),
                    {},
                    self.output_path,
                )
            )
        email_delta.assert_called()
        delta = email_delta.call_args[0][0]

        self.assertEqual(delta.user, workflow.owner)
        self.assertEqual(delta.workflow, workflow)
        self.assertEqual(delta.wf_module, wf_module)
        self.assertEqual(delta.old_result, RenderResult(arrow_table({"A": [1]})))
        self.assertEqual(delta.new_result, RenderResult(arrow_table({"A": [2]})))

    @patch.object(rabbitmq, "send_update_to_workflow_clients", noop)
    @patch.object(rendercache, "open_cached_render_result")
    @patch.object(notifications, "email_output_delta")
    def test_email_delta_ignore_corrupt_cache_error(self, email_delta, read_cache):
        read_cache.side_effect = rendercache.CorruptCacheError
        workflow = Workflow.create_and_init()
        tab = workflow.tabs.first()
        wf_module = tab.wf_modules.create(
            order=0,
            slug="step-1",
            module_id_name="x",
            last_relevant_delta_id=workflow.last_delta_id - 1,
            notifications=True,
        )
        # We need to actually populate the cache to set up the test. The code
        # under test will only try to open the render result if the database
        # says there's something there.
        rendercache.cache_render_result(
            workflow,
            wf_module,
            workflow.last_delta_id - 1,
            RenderResult(arrow_table({"A": [1]})),
        )
        wf_module.last_relevant_delta_id = workflow.last_delta_id
        wf_module.save(update_fields=["last_relevant_delta_id"])

        module_zipfile = create_module_zipfile(
            "x",
            # returns different data -- but CorruptCacheError means we won't care.
            python_code='import pandas as pd\ndef render(table, params): return pd.DataFrame({"A": [2]})',
        )

        with self.assertLogs(level=logging.ERROR):
            self.run_with_async_db(
                execute_wfmodule(
                    self.chroot_context,
                    workflow,
                    wf_module,
                    module_zipfile,
                    {},
                    Tab(tab.slug, tab.name),
                    RenderResult(),
                    {},
                    self.output_path,
                )
            )

        email_delta.assert_not_called()

    @patch.object(rabbitmq, "send_update_to_workflow_clients", noop)
    def test_fetch_result_happy_path(self):
        workflow = Workflow.create_and_init()
        tab = workflow.tabs.first()
        wf_module = tab.wf_modules.create(
            order=0,
            slug="step-1",
            module_id_name="x",
            last_relevant_delta_id=workflow.last_delta_id,
            fetch_errors=[
                RenderError(I18nMessage("foo", {}, "module")),
                RenderError(I18nMessage("bar", {"x": "y"}, "cjwmodule")),
            ],
        )
        with parquet_file({"A": [1]}) as path:
            so = create_stored_object(workflow.id, wf_module.id, path)
        wf_module.stored_data_version = so.stored_at
        wf_module.save(update_fields=["stored_data_version"])

        module_zipfile = create_module_zipfile(
            "x",
            python_code=textwrap.dedent(
                """
                import pyarrow as pa
                import pandas as pd
                from pandas.testing import assert_frame_equal
                from cjwkernel.types import RenderError, I18nMessage

                def render(table, params, *, fetch_result, **kwargs):
                    assert fetch_result.errors == [
                        RenderError(I18nMessage("foo", {}, "module")),
                        RenderError(I18nMessage("bar", {"x": "y"}, "cjwmodule")),
                    ]
                    fetch_dataframe = pa.parquet.read_table(str(fetch_result.path))
                    assert_frame_equal(fetch_dataframe, pd.DataFrame({"A": [1]}))
                    return pd.DataFrame()
                """
            ),
        )

        with self.assertLogs(level=logging.INFO):
            self.run_with_async_db(
                execute_wfmodule(
                    self.chroot_context,
                    workflow,
                    wf_module,
                    module_zipfile,
                    {},
                    Tab(tab.slug, tab.name),
                    RenderResult(),
                    {},
                    self.output_path,
                )
            )

    @patch.object(rabbitmq, "send_update_to_workflow_clients", noop)
    def test_fetch_result_deleted_file_means_none(self):
        workflow = Workflow.create_and_init()
        tab = workflow.tabs.first()
        wf_module = tab.wf_modules.create(
            order=0,
            slug="step-1",
            module_id_name="x",
            last_relevant_delta_id=workflow.last_delta_id,
        )
        with parquet_file({"A": [1]}) as path:
            so = create_stored_object(workflow.id, wf_module.id, path)
        wf_module.stored_data_version = so.stored_at
        wf_module.save(update_fields=["stored_data_version"])
        # Now delete the file on S3 -- but leave the DB pointing to it.
        minio.remove(minio.StoredObjectsBucket, so.key)

        def render(*args, fetch_result, **kwargs):
            self.assertIsNone(fetch_result)
            return RenderResult()

        module_zipfile = create_module_zipfile(
            "x",
            python_code=textwrap.dedent(
                """
                import pandas as pd
                def render(table, params, *, fetch_result, **kwargs):
                    assert fetch_result is None
                    return pd.DataFrame()
                """
            ),
        )

        with self.assertLogs(level=logging.INFO):
            self.run_with_async_db(
                execute_wfmodule(
                    self.chroot_context,
                    workflow,
                    wf_module,
                    module_zipfile,
                    {},
                    Tab(tab.slug, tab.name),
                    RenderResult(),
                    {},
                    self.output_path,
                )
            )

    @patch.object(rabbitmq, "send_update_to_workflow_clients", noop)
    def test_fetch_result_deleted_stored_object_means_none(self):
        workflow = Workflow.create_and_init()
        tab = workflow.tabs.first()
        wf_module = tab.wf_modules.create(
            order=0,
            slug="step-1",
            module_id_name="x",
            last_relevant_delta_id=workflow.last_delta_id,
            # wf_module.stored_data_version is buggy: it can point at a nonexistent
            # StoredObject. Let's do that.
            stored_data_version=timezone.now(),
        )

        module_zipfile = create_module_zipfile(
            "x",
            python_code=textwrap.dedent(
                """
                import pandas as pd
                def render(table, params, *, fetch_result, **kwargs):
                    assert fetch_result is None
                    return pd.DataFrame()
                """
            ),
        )

        with self.assertLogs(level=logging.INFO):
            self.run_with_async_db(
                execute_wfmodule(
                    self.chroot_context,
                    workflow,
                    wf_module,
                    module_zipfile,
                    {},
                    Tab(tab.slug, tab.name),
                    RenderResult(),
                    {},
                    self.output_path,
                )
            )

    @patch.object(rabbitmq, "send_update_to_workflow_clients", noop)
    def test_fetch_result_no_stored_object_means_none(self):
        workflow = Workflow.create_and_init()
        tab = workflow.tabs.first()
        wf_module = tab.wf_modules.create(
            order=0,
            slug="step-1",
            module_id_name="x",
            last_relevant_delta_id=workflow.last_delta_id,
        )

        module_zipfile = create_module_zipfile(
            "x",
            python_code=textwrap.dedent(
                """
                import pandas as pd
                def render(table, params, *, fetch_result, **kwargs):
                    assert fetch_result is None
                    return pd.DataFrame()
                """
            ),
        )

        with self.assertLogs(level=logging.INFO):
            self.run_with_async_db(
                execute_wfmodule(
                    self.chroot_context,
                    workflow,
                    wf_module,
                    module_zipfile,
                    {},
                    Tab(tab.slug, tab.name),
                    RenderResult(),
                    {},
                    self.output_path,
                )
            )

    @patch.object(rabbitmq, "send_update_to_workflow_clients", noop)
    def test_fetch_result_no_bucket_or_key_stored_object_means_none(self):
        workflow = Workflow.create_and_init()
        tab = workflow.tabs.first()
        wf_module = tab.wf_modules.create(
            order=0,
            slug="step-1",
            module_id_name="x",
            last_relevant_delta_id=workflow.last_delta_id,
            stored_data_version=timezone.now(),
        )
        wf_module.stored_objects.create(
            stored_at=wf_module.stored_data_version, key="", size=0, hash="whatever"
        )

        module_zipfile = create_module_zipfile(
            "x",
            python_code=textwrap.dedent(
                """
                import pandas as pd
                def render(table, params, *, fetch_result, **kwargs):
                    assert fetch_result is None
                    return pd.DataFrame()
                """
            ),
        )

        with self.assertLogs(level=logging.INFO):
            self.run_with_async_db(
                execute_wfmodule(
                    self.chroot_context,
                    workflow,
                    wf_module,
                    module_zipfile,
                    {},
                    Tab(tab.slug, tab.name),
                    RenderResult(),
                    {},
                    self.output_path,
                )
            )

    @patch.object(rabbitmq, "send_update_to_workflow_clients", noop)
    def test_report_module_error(self):
        workflow = Workflow.create_and_init()
        tab = workflow.tabs.first()
        wf_module = tab.wf_modules.create(
            order=0,
            slug="step-1",
            module_id_name="x",
            last_relevant_delta_id=workflow.last_delta_id,
        )

        module_zipfile = create_module_zipfile(
            "x", python_code="def render(table, params):\n  undefined()"
        )

        with self.assertLogs(level=logging.INFO):
            result = self.run_with_async_db(
                execute_wfmodule(
                    self.chroot_context,
                    workflow,
                    wf_module,
                    module_zipfile,
                    {},
                    Tab(tab.slug, tab.name),
                    RenderResult(),
                    {},
                    self.output_path,
                )
            )
        self.assertEqual(
            result,
            RenderResult(
                errors=[
                    RenderError(
                        I18nMessage(
                            "py.renderer.execute.wf_module.user_visible_bug_during_render",
                            {
                                "message": "exit code 1: NameError: name 'undefined' is not defined"
                            },
                        )
                    )
                ]
            ),
        )
