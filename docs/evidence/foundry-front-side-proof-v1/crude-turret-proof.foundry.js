foundry.note('Front-side shared-cage workflow proof',{workflowFixture:true,views:['front','side']});
foundry.validation.productionBudget({"asset":{"maxVertices":700,"maxTriangles":1200},"components":{"Crude_Turret_Volume":{"maxVertices":700,"maxTriangles":1200}},"scene":{"instances":1,"maxExpandedVertices":700,"maxExpandedTriangles":1200}});
foundry.material.create('neutral-proof',{baseColor:[0.46,0.48,0.47,1],metallic:0,roughness:1});
foundry.scene.createSubdivisionCage('shared-proof-cage',{"base":"box","segments":[3,2,2],"size":[2.2,1.2,1.6]});
foundry.mesh.fitSubdivisionCage('shared-proof-cage',{views:['front','side'],levels:2,maxEvaluations:4096});
foundry.mesh.subdivide('shared-proof-cage',{"scheme":"catmull-clark","levels":2,"output":"Crude_Turret_Volume","material":"neutral-proof","topology":{"coverage":"all_output_vertices","purpose":"silhouette","rationale":"One shared fitted cage carries both declared synthetic silhouettes.","maxOutputVertices":700,"maxOutputTriangles":1200,"maxGrowthRatio":32,"simplification":{"method":"remove_or_merge","status":"pending_review","maxVisibleErrorPx":0.75}}});
foundry.review.modelSheet({cage:'shared-proof-cage',target:'Crude_Turret_Volume',views:['front','side']});
foundry.validation.assert('model_sheet_fit',{minIou:0.92,maxP95BoundaryErrorRingFraction:0.02,maxLandmarkErrorRingFraction:0.01});
