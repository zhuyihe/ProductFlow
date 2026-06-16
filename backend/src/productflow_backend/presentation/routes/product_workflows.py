from __future__ import annotations

from fastapi import APIRouter, Depends, File, Form, UploadFile, status
from sqlalchemy.orm import Session

from productflow_backend.application.audit_logs import AuditRequestContext, record_admin_user_content_access
from productflow_backend.application.auth_sessions import Principal
from productflow_backend.application.product_workflows import (
    apply_node_group_template_to_workflow,
    archive_user_canvas_template,
    bind_workflow_node_image,
    cancel_product_workflow_run,
    create_user_canvas_template_from_workflow_nodes,
    create_workflow_edge,
    create_workflow_node,
    delete_workflow_edge,
    delete_workflow_node,
    duplicate_workflow_node_group,
    get_or_create_product_workflow,
    get_product_workflow_status,
    list_canvas_templates,
    rename_user_canvas_template,
    retry_product_workflow_run,
    submit_product_workflow_run,
    update_workflow_copy_set,
    update_workflow_node,
    upload_workflow_node_image,
)
from productflow_backend.presentation.deps import (
    current_principal,
    current_workspace_owner_user_id,
    get_session,
    request_audit_context,
    require_workspace_principal,
)
from productflow_backend.presentation.schemas.product_workflows import (
    ApplyWorkflowTemplateGroupRequest,
    BindWorkflowNodeImageRequest,
    CanvasTemplateListResponse,
    CanvasTemplateSummaryResponse,
    CreateUserTemplateGroupRequest,
    CreateWorkflowEdgeRequest,
    CreateWorkflowNodeRequest,
    DuplicateWorkflowNodeGroupRequest,
    ProductWorkflowResponse,
    ProductWorkflowStatusResponse,
    RunWorkflowRequest,
    UpdateUserTemplateGroupRequest,
    UpdateWorkflowCopySetRequest,
    UpdateWorkflowNodeRequest,
    serialize_canvas_template_summary,
    serialize_product_workflow,
    serialize_product_workflow_status,
    serialize_user_canvas_template_summary,
)
from productflow_backend.presentation.upload_validation import read_validated_image_upload

router = APIRouter(prefix="/api", tags=["product-workflows"], dependencies=[Depends(require_workspace_principal)])


def _record_workflow_audit(
    session: Session,
    *,
    principal: Principal | None,
    workflow,
    action: str,
    resource_type: str,
    resource_id: str,
    audit_context: AuditRequestContext,
) -> None:
    if principal is None:
        return
    record_admin_user_content_access(
        session,
        principal=principal,
        target_user_id=workflow.product.owner_user_id,
        action=action,
        resource_type=resource_type,
        resource_id=resource_id,
        request_context=audit_context,
    )


@router.get("/products/{product_id}/workflow", response_model=ProductWorkflowResponse)
def get_product_workflow_endpoint(
    product_id: str,
    session: Session = Depends(get_session),
    principal: Principal = Depends(require_workspace_principal),
    owner_user_id: str = Depends(current_workspace_owner_user_id),
    audit_context: AuditRequestContext = Depends(request_audit_context),
) -> ProductWorkflowResponse:
    workflow = get_or_create_product_workflow(session, product_id, owner_user_id)
    _record_workflow_audit(
        session,
        principal=principal,
        workflow=workflow,
        action="read",
        resource_type="product_workflow",
        resource_id=workflow.id,
        audit_context=audit_context,
    )
    return serialize_product_workflow(workflow)


@router.get("/products/{product_id}/workflow/status", response_model=ProductWorkflowStatusResponse)
def get_product_workflow_status_endpoint(
    product_id: str,
    session: Session = Depends(get_session),
    principal: Principal = Depends(require_workspace_principal),
    owner_user_id: str = Depends(current_workspace_owner_user_id),
    audit_context: AuditRequestContext = Depends(request_audit_context),
) -> ProductWorkflowStatusResponse:
    workflow = get_product_workflow_status(session, product_id, owner_user_id)
    _record_workflow_audit(
        session,
        principal=principal,
        workflow=workflow.workflow,
        action="read",
        resource_type="product_workflow_status",
        resource_id=workflow.workflow.id,
        audit_context=audit_context,
    )
    return serialize_product_workflow_status(workflow)


@router.get("/workflow/canvas-templates", response_model=CanvasTemplateListResponse)
def list_canvas_templates_endpoint(
    session: Session = Depends(get_session),
    owner_user_id: str = Depends(current_workspace_owner_user_id),
) -> CanvasTemplateListResponse:
    templates = [
        serialize_canvas_template_summary(template)
        for template in list_canvas_templates(session, owner_user_id=owner_user_id)
    ]
    return CanvasTemplateListResponse(items=templates)


@router.post(
    "/products/{product_id}/workflow/user-template-groups",
    response_model=CanvasTemplateSummaryResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_user_template_group_endpoint(
    product_id: str,
    payload: CreateUserTemplateGroupRequest,
    session: Session = Depends(get_session),
    principal: Principal = Depends(require_workspace_principal),
    owner_user_id: str = Depends(current_workspace_owner_user_id),
    audit_context: AuditRequestContext = Depends(request_audit_context),
) -> CanvasTemplateSummaryResponse:
    template = create_user_canvas_template_from_workflow_nodes(
        session,
        product_id=product_id,
        owner_user_id=owner_user_id,
        title=payload.title,
        description=payload.description,
        node_ids=payload.node_ids,
    )
    if principal.is_admin:
        workflow = get_or_create_product_workflow(session, product_id, owner_user_id)
        _record_workflow_audit(
            session,
            principal=principal,
            workflow=workflow,
            action="create",
            resource_type="user_canvas_template",
            resource_id=template.id,
            audit_context=audit_context,
        )
    return serialize_user_canvas_template_summary(template)


@router.patch("/workflow/user-template-groups/{template_id}", response_model=CanvasTemplateSummaryResponse)
def update_user_template_group_endpoint(
    template_id: str,
    payload: UpdateUserTemplateGroupRequest,
    session: Session = Depends(get_session),
    principal: Principal = Depends(require_workspace_principal),
    owner_user_id: str = Depends(current_workspace_owner_user_id),
    audit_context: AuditRequestContext = Depends(request_audit_context),
) -> CanvasTemplateSummaryResponse:
    template = rename_user_canvas_template(
        session,
        template_id=template_id,
        owner_user_id=owner_user_id,
        title=payload.title,
        description=payload.description,
    )
    record_admin_user_content_access(
        session,
        principal=principal,
        target_user_id=template.owner_user_id,
        action="update",
        resource_type="user_canvas_template",
        resource_id=template.id,
        request_context=audit_context,
    )
    return serialize_user_canvas_template_summary(template)


@router.delete("/workflow/user-template-groups/{template_id}", status_code=status.HTTP_204_NO_CONTENT)
def archive_user_template_group_endpoint(
    template_id: str,
    session: Session = Depends(get_session),
    principal: Principal = Depends(require_workspace_principal),
    owner_user_id: str = Depends(current_workspace_owner_user_id),
    audit_context: AuditRequestContext = Depends(request_audit_context),
) -> None:
    template = archive_user_canvas_template(session, template_id=template_id, owner_user_id=owner_user_id)
    record_admin_user_content_access(
        session,
        principal=principal,
        target_user_id=template.owner_user_id,
        action="delete",
        resource_type="user_canvas_template",
        resource_id=template_id,
        request_context=audit_context,
    )


@router.post(
    "/products/{product_id}/workflow/nodes",
    response_model=ProductWorkflowResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_workflow_node_endpoint(
    product_id: str,
    payload: CreateWorkflowNodeRequest,
    session: Session = Depends(get_session),
    principal: Principal = Depends(require_workspace_principal),
    owner_user_id: str = Depends(current_workspace_owner_user_id),
    audit_context: AuditRequestContext = Depends(request_audit_context),
) -> ProductWorkflowResponse:
    workflow = create_workflow_node(
        session,
        product_id=product_id,
        owner_user_id=owner_user_id,
        node_type=payload.node_type,
        title=payload.title,
        position_x=payload.position_x,
        position_y=payload.position_y,
        config_json=payload.config_json,
    )
    _record_workflow_audit(
        session,
        principal=principal,
        workflow=workflow,
        action="create",
        resource_type="workflow_node",
        resource_id=product_id,
        audit_context=audit_context,
    )
    return serialize_product_workflow(workflow)


@router.post(
    "/products/{product_id}/workflow/template-groups",
    response_model=ProductWorkflowResponse,
    status_code=status.HTTP_201_CREATED,
)
def apply_workflow_template_group_endpoint(
    product_id: str,
    payload: ApplyWorkflowTemplateGroupRequest,
    session: Session = Depends(get_session),
    principal: Principal = Depends(require_workspace_principal),
    owner_user_id: str = Depends(current_workspace_owner_user_id),
    audit_context: AuditRequestContext = Depends(request_audit_context),
) -> ProductWorkflowResponse:
    workflow = apply_node_group_template_to_workflow(
        session,
        product_id=product_id,
        template_key=payload.template_key,
        position_x=payload.position_x,
        position_y=payload.position_y,
        owner_user_id=owner_user_id,
    )
    _record_workflow_audit(
        session,
        principal=principal,
        workflow=workflow,
        action="apply_template",
        resource_type="product_workflow",
        resource_id=workflow.id,
        audit_context=audit_context,
    )
    return serialize_product_workflow(workflow)


@router.post(
    "/products/{product_id}/workflow/node-groups/duplicate",
    response_model=ProductWorkflowResponse,
    status_code=status.HTTP_201_CREATED,
)
def duplicate_workflow_node_group_endpoint(
    product_id: str,
    payload: DuplicateWorkflowNodeGroupRequest,
    session: Session = Depends(get_session),
    principal: Principal = Depends(require_workspace_principal),
    owner_user_id: str = Depends(current_workspace_owner_user_id),
    audit_context: AuditRequestContext = Depends(request_audit_context),
) -> ProductWorkflowResponse:
    workflow = duplicate_workflow_node_group(
        session,
        product_id=product_id,
        node_ids=payload.node_ids,
        owner_user_id=owner_user_id,
        position_x=payload.position_x,
        position_y=payload.position_y,
        offset_x=payload.offset_x,
        offset_y=payload.offset_y,
    )
    _record_workflow_audit(
        session,
        principal=principal,
        workflow=workflow,
        action="duplicate",
        resource_type="workflow_node_group",
        resource_id=product_id,
        audit_context=audit_context,
    )
    return serialize_product_workflow(workflow)


@router.patch("/workflow-nodes/{node_id}", response_model=ProductWorkflowResponse)
def update_workflow_node_endpoint(
    node_id: str,
    payload: UpdateWorkflowNodeRequest,
    session: Session = Depends(get_session),
    principal: Principal = Depends(require_workspace_principal),
    owner_user_id: str = Depends(current_workspace_owner_user_id),
    audit_context: AuditRequestContext = Depends(request_audit_context),
) -> ProductWorkflowResponse:
    workflow = update_workflow_node(
        session,
        node_id=node_id,
        owner_user_id=owner_user_id,
        title=payload.title,
        position_x=payload.position_x,
        position_y=payload.position_y,
        config_json=payload.config_json,
    )
    _record_workflow_audit(
        session,
        principal=principal,
        workflow=workflow,
        action="update",
        resource_type="workflow_node",
        resource_id=node_id,
        audit_context=audit_context,
    )
    return serialize_product_workflow(workflow)


@router.patch("/workflow-nodes/{node_id}/copy", response_model=ProductWorkflowResponse)
def update_workflow_copy_set_endpoint(
    node_id: str,
    payload: UpdateWorkflowCopySetRequest,
    session: Session = Depends(get_session),
    principal: Principal = Depends(require_workspace_principal),
    owner_user_id: str = Depends(current_workspace_owner_user_id),
    audit_context: AuditRequestContext = Depends(request_audit_context),
) -> ProductWorkflowResponse:
    workflow = update_workflow_copy_set(
        session,
        node_id=node_id,
        structured_payload=payload.structured_payload,
        owner_user_id=owner_user_id,
    )
    _record_workflow_audit(
        session,
        principal=principal,
        workflow=workflow,
        action="update",
        resource_type="workflow_copy",
        resource_id=node_id,
        audit_context=audit_context,
    )
    return serialize_product_workflow(workflow)


@router.post("/workflow-nodes/{node_id}/image", response_model=ProductWorkflowResponse)
async def upload_workflow_node_image_endpoint(
    node_id: str,
    image: UploadFile = File(...),
    role: str | None = Form(default=None),
    label: str | None = Form(default=None),
    session: Session = Depends(get_session),
    principal: Principal = Depends(require_workspace_principal),
    owner_user_id: str = Depends(current_workspace_owner_user_id),
    audit_context: AuditRequestContext = Depends(request_audit_context),
) -> ProductWorkflowResponse:
    validated = await read_validated_image_upload(image, fallback_filename="workflow-image.bin")
    workflow = upload_workflow_node_image(
        session,
        node_id=node_id,
        owner_user_id=owner_user_id,
        image_bytes=validated.content,
        filename=validated.filename,
        content_type=validated.mime_type,
        role=role,
        label=label,
    )
    _record_workflow_audit(
        session,
        principal=principal,
        workflow=workflow,
        action="upload",
        resource_type="workflow_node_image",
        resource_id=node_id,
        audit_context=audit_context,
    )
    return serialize_product_workflow(workflow)


@router.post("/workflow-nodes/{node_id}/image-source", response_model=ProductWorkflowResponse)
def bind_workflow_node_image_endpoint(
    node_id: str,
    payload: BindWorkflowNodeImageRequest,
    session: Session = Depends(get_session),
    principal: Principal = Depends(require_workspace_principal),
    owner_user_id: str = Depends(current_workspace_owner_user_id),
    audit_context: AuditRequestContext = Depends(request_audit_context),
) -> ProductWorkflowResponse:
    workflow = bind_workflow_node_image(
        session,
        node_id=node_id,
        owner_user_id=owner_user_id,
        source_asset_id=payload.source_asset_id,
        poster_variant_id=payload.poster_variant_id,
    )
    _record_workflow_audit(
        session,
        principal=principal,
        workflow=workflow,
        action="bind_image",
        resource_type="workflow_node",
        resource_id=node_id,
        audit_context=audit_context,
    )
    return serialize_product_workflow(workflow)


@router.post(
    "/products/{product_id}/workflow/edges",
    response_model=ProductWorkflowResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_workflow_edge_endpoint(
    product_id: str,
    payload: CreateWorkflowEdgeRequest,
    session: Session = Depends(get_session),
    principal: Principal = Depends(require_workspace_principal),
    owner_user_id: str = Depends(current_workspace_owner_user_id),
    audit_context: AuditRequestContext = Depends(request_audit_context),
) -> ProductWorkflowResponse:
    workflow = create_workflow_edge(
        session,
        product_id=product_id,
        owner_user_id=owner_user_id,
        source_node_id=payload.source_node_id,
        target_node_id=payload.target_node_id,
        source_handle=payload.source_handle,
        target_handle=payload.target_handle,
    )
    _record_workflow_audit(
        session,
        principal=principal,
        workflow=workflow,
        action="create",
        resource_type="workflow_edge",
        resource_id=product_id,
        audit_context=audit_context,
    )
    return serialize_product_workflow(workflow)


@router.delete("/workflow-edges/{edge_id}", response_model=ProductWorkflowResponse)
def delete_workflow_edge_endpoint(
    edge_id: str,
    session: Session = Depends(get_session),
    principal: Principal = Depends(require_workspace_principal),
    owner_user_id: str = Depends(current_workspace_owner_user_id),
    audit_context: AuditRequestContext = Depends(request_audit_context),
) -> ProductWorkflowResponse:
    workflow = delete_workflow_edge(session, edge_id=edge_id, owner_user_id=owner_user_id)
    _record_workflow_audit(
        session,
        principal=principal,
        workflow=workflow,
        action="delete",
        resource_type="workflow_edge",
        resource_id=edge_id,
        audit_context=audit_context,
    )
    return serialize_product_workflow(workflow)


@router.delete("/workflow-nodes/{node_id}", response_model=ProductWorkflowResponse)
def delete_workflow_node_endpoint(
    node_id: str,
    session: Session = Depends(get_session),
    principal: Principal = Depends(require_workspace_principal),
    owner_user_id: str = Depends(current_workspace_owner_user_id),
    audit_context: AuditRequestContext = Depends(request_audit_context),
) -> ProductWorkflowResponse:
    workflow = delete_workflow_node(session, node_id=node_id, owner_user_id=owner_user_id)
    _record_workflow_audit(
        session,
        principal=principal,
        workflow=workflow,
        action="delete",
        resource_type="workflow_node",
        resource_id=node_id,
        audit_context=audit_context,
    )
    return serialize_product_workflow(workflow)


@router.post("/products/{product_id}/workflow/run", response_model=ProductWorkflowResponse)
def run_product_workflow_endpoint(
    product_id: str,
    payload: RunWorkflowRequest | None = None,
    session: Session = Depends(get_session),
    principal: Principal | None = Depends(current_principal),
    owner_user_id: str = Depends(current_workspace_owner_user_id),
    audit_context: AuditRequestContext = Depends(request_audit_context),
) -> ProductWorkflowResponse:
    workflow = submit_product_workflow_run(
        session,
        product_id=product_id,
        owner_user_id=owner_user_id,
        start_node_id=payload.start_node_id if payload else None,
        principal=principal,
        image_model=payload.image_model if payload else None,
        text_model=payload.text_model if payload else None,
    )
    _record_workflow_audit(
        session,
        principal=principal,
        workflow=workflow,
        action="run",
        resource_type="product_workflow",
        resource_id=workflow.id,
        audit_context=audit_context,
    )
    return serialize_product_workflow(workflow)


@router.post("/products/{product_id}/workflow/runs/{run_id}/cancel", response_model=ProductWorkflowResponse)
def cancel_product_workflow_run_endpoint(
    product_id: str,
    run_id: str,
    session: Session = Depends(get_session),
    principal: Principal = Depends(require_workspace_principal),
    owner_user_id: str = Depends(current_workspace_owner_user_id),
    audit_context: AuditRequestContext = Depends(request_audit_context),
) -> ProductWorkflowResponse:
    workflow = cancel_product_workflow_run(
        session,
        product_id=product_id,
        run_id=run_id,
        owner_user_id=owner_user_id,
    )
    _record_workflow_audit(
        session,
        principal=principal,
        workflow=workflow,
        action="cancel",
        resource_type="workflow_run",
        resource_id=run_id,
        audit_context=audit_context,
    )
    return serialize_product_workflow(workflow)


@router.post(
    "/products/{product_id}/workflow/runs/{run_id}/retry",
    response_model=ProductWorkflowResponse,
    status_code=status.HTTP_202_ACCEPTED,
)
def retry_product_workflow_run_endpoint(
    product_id: str,
    run_id: str,
    session: Session = Depends(get_session),
    principal: Principal | None = Depends(current_principal),
    owner_user_id: str = Depends(current_workspace_owner_user_id),
    audit_context: AuditRequestContext = Depends(request_audit_context),
) -> ProductWorkflowResponse:
    workflow = retry_product_workflow_run(
        session,
        product_id=product_id,
        run_id=run_id,
        owner_user_id=owner_user_id,
        principal=principal,
    )
    _record_workflow_audit(
        session,
        principal=principal,
        workflow=workflow,
        action="retry",
        resource_type="workflow_run",
        resource_id=run_id,
        audit_context=audit_context,
    )
    return serialize_product_workflow(workflow)
