import bpy
import os
import time
#########################################
# Set vars
#########################################

scene = bpy.context.scene
# start = bpy.context.scene.frame_start
# end = bpy.context.scene.frame_end
start = 0
end = 3
scene.frame_set( start )
output_dir = bpy.path.abspath("//") + 'exports' +'_' + str( round( time.time() ) ) + '/'
print( 'Exporting to ' + output_dir )
if not os.path.exists(output_dir):
    os.makedirs(output_dir)

bakeFloorShadow = True
bakeFloorEmission = True
bakeGeoShadow = True
bakeGeoNormal = True
bakeGeoDiffuse = True
bakeGeoRoughness = True

#########################################
# Renderer
#########################################
bpy.context.scene.render.engine = 'CYCLES'
bpy.context.scene.cycles.device = 'GPU'
bpy.context.scene.cycles.use_denoising = True
bpy.context.scene.cycles.samples = 32
bpy.context.scene.render.tile_x = 256
bpy.context.scene.render.tile_y = 256
bpy.context.scene.render.bake.margin = 4

#########################################
# Init
#########################################
bpy.ops.object.mode_set(mode = 'OBJECT')
bpy.ops.object.select_all(action='DESELECT')
meshArray = []
for obj in bpy.context.scene.objects:
    if obj.type == 'MESH': 
        meshArray.append( obj.name )
        if 'Logo' in obj.name:
            bpy.context.view_layer.objects.active = obj
            bpy.context.object.hide_render = True


# scene.frame_set( 35 )

def appendImageToMaterial( obj, image ):
    bpy.ops.object.select_all(action='DESELECT')
    obj.select_set( True )
    bpy.context.view_layer.objects.active = obj
    
    for mat in obj.data.materials:
        mat.use_nodes = True
        nodes = mat.node_tree.nodes
        node = nodes.new('ShaderNodeTexImage')
        node.image = image
        node.location = (100,100)
        node.select = True
        nodes.active = node

#########################################
# Switch render settings
#########################################

def setRenderer( mode ):
    if mode == 'combined' :
        bpy.context.scene.cycles.bake_type = 'COMBINED'
        bpy.context.scene.render.bake.use_pass_direct = True
        bpy.context.scene.render.bake.use_pass_indirect = True
        bpy.context.scene.render.bake.use_pass_diffuse = True
        bpy.context.scene.render.bake.use_pass_glossy = False
        bpy.context.scene.render.bake.use_pass_transmission = False
        bpy.context.scene.render.bake.use_pass_ambient_occlusion = True
        bpy.context.scene.render.bake.use_pass_emit = False
    if mode == 'roughness' :
        bpy.context.scene.cycles.bake_type = 'ROUGHNESS'
    if mode == 'diffuse' :
        bpy.context.scene.cycles.bake_type = 'DIFFUSE'
        bpy.context.scene.render.bake.use_pass_direct = False
        bpy.context.scene.render.bake.use_pass_indirect = False
    if mode == 'normal' :
        bpy.context.scene.cycles.bake_type = 'NORMAL'
    if mode == 'emission' :
        bpy.context.scene.cycles.bake_type = 'COMBINED'
        bpy.context.scene.render.bake.use_pass_direct = False
        bpy.context.scene.render.bake.use_pass_indirect = True
        bpy.context.scene.render.bake.use_pass_diffuse = True
        bpy.context.scene.render.bake.use_pass_glossy = False
        bpy.context.scene.render.bake.use_pass_transmission = False
        bpy.context.scene.render.bake.use_pass_ambient_occlusion = False
        bpy.context.scene.render.bake.use_pass_emit = False
        
#########################################
# Geos bake SINGLE MAPS
#########################################

def bake_map( mapId ):
    
    setRenderer( mapId )
    for collection in bpy.data.collections:
        if 'Letter_group' in collection.name:
            bpy.ops.image.new(name=collection.name+'_' + mapId, width=1024, height=1024)
            image = bpy.data.images[collection.name+'_' + mapId ]

            for mat in bpy.data.materials:
                mat.use_nodes = True
                nodes = mat.node_tree.nodes
                node = nodes.new('ShaderNodeTexImage')
                node.image = image
                node.location = (100,100)
                node.select = True
                nodes.active = node
            
            for obj in collection.all_objects:      
                if obj.type == 'MESH':
                    obj.select_set( True )
                    bpy.context.view_layer.objects.active = obj

        scene.frame_set( 10 )
        bpy.ops.object.bake(type=bpy.context.scene.cycles.bake_type)
        image.filepath_raw = output_dir + collection.name + '_' + mapId + '.png'
        image.file_format = 'PNG'
        print( '------------------------------> _' + mapId + ' was saved' )
        image.save()

#########################################
# Plane bake
#########################################
def bake_plane():
    bakeDir = output_dir + 'plane_shadow/'
    os.makedirs( bakeDir )

    setRenderer( 'combined' )
    
    bpy.ops.object.select_all(action='DESELECT')
    matching = [s for s in meshArray if "Plane" in s ]
    plane = bpy.data.objects[ matching[ 0 ] ]
    bpy.ops.image.new(name='Plane_shadow', width=1024, height=1024)
    image = bpy.data.images['Plane_shadow']
    appendImageToMaterial( plane, image )
    plane.select_set( True )
    bpy.context.view_layer.objects.active = plane
    for frame in range(end):
        scene.frame_set( frame )
        bpy.ops.object.bake(type=bpy.context.scene.cycles.bake_type)
        image.filepath_raw = bakeDir + 'plane_shadow_' + str( frame ) + '.png'
        image.file_format = 'PNG'
        print( '------------------------------> Frame %s was saved to %s' % (str( frame ), image.filepath_raw ) )
        image.save()



#########################################
# Plane bake emissive
#########################################

def bake_emissive():
    setRenderer( 'emission' )
    emiColors = [ (1, 0, 0, 1), (0, 1, 0, 1), (0, 0, 1, 1) ]
    emiColors2 = [ (0.05, 0, 0, 1), (0, 0.05, 0, 1), (0, 0, 0.05, 1) ]
    colIndex = 0
    for collection in bpy.data.collections:
        for c in bpy.data.collections:
            c.hide_render = True
        collection.hide_render = False
        if 'Letter_group' in collection.name:
            objindex = 0
            for obj in collection.all_objects:
                if obj.type == 'MESH':
                    for mat in obj.data.materials:
                        if "Letter" in mat.name:
                            om = mat
                            pm = mat
                            nm = mat.copy()
                            nm.name = om.name + '_emi_' + str( objindex )
                            nm.node_tree.nodes["Principled BSDF"].inputs[0].default_value = emiColors[ objindex ]
                            materialnum = len( obj.data.materials )
                            for i in range(0,materialnum):
                                if obj.data.materials[i] == om:
                                    obj.data.materials[i] = nm
                        if "Inner" in mat.name:
                            om = mat
                            pmi = mat
                            nm = mat.copy()
                            nm.name = om.name + '_emi_' + str( objindex )
                            nm.node_tree.nodes["Principled BSDF"].inputs[0].default_value = emiColors[ objindex ]
                            nm.node_tree.nodes["Principled BSDF"].inputs[17].default_value = emiColors2[ objindex ]
                            materialnum = len( obj.data.materials )
                            for i in range(0,materialnum):
                                if obj.data.materials[i] == om:
                                    obj.data.materials[i] = nm
                    objindex += 1
            # Colors swapped, do bake

            bpy.ops.object.select_all(action='DESELECT')
            bakeDir = output_dir + collection.name + '_emission/'
            os.makedirs( bakeDir )
            bpy.ops.object.select_all(action='DESELECT')
            matching = [s for s in meshArray if "Plane" in s ]
            plane = bpy.data.objects[ matching[ 0 ] ]
            bpy.ops.image.new(name='Plane_emission_' + collection.name, width=1024, height=1024)
            image = bpy.data.images['Plane_emission_' + collection.name]
            appendImageToMaterial( plane, image )
            plane.select_set( True )
            bpy.context.view_layer.objects.active = plane
            for frame in range(end):
                scene.frame_set( frame )
                bpy.ops.object.bake(type=bpy.context.scene.cycles.bake_type)
                image.filepath_raw = bakeDir + collection.name + '_emission_' + str( frame ) + '.png'
                image.file_format = 'PNG'
                print( '------------------------------> Frame %s for ' % ( str( frame ) ) + collection.name  + ' emission was saved to %s' % ( image.filepath_raw ) )
                image.save()

            # Restore color
            for obj in collection.all_objects:
                if obj.type == 'MESH':
                    for mat in obj.data.materials:
                        if "Letter" in mat.name:
                            om = mat
                            materialnum = len( obj.data.materials )
                            for i in range(0,materialnum):
                                if obj.data.materials[i] == om:
                                    obj.data.materials[i] = pm
                        if "Inner" in mat.name:
                            om = mat
                            materialnum = len( obj.data.materials )
                            for i in range(0,materialnum):
                                if obj.data.materials[i] == om:
                                    obj.data.materials[i] = pmi
        colIndex += 1
                    

#########################################
# Geos bake shadow
#########################################
def bake_geos():
    setRenderer( 'combined' )
    
    for collection in bpy.data.collections:
        if 'Letter_group' in collection.name:
            bpy.ops.object.select_all(action='DESELECT')
            bakeDir = output_dir + collection.name + '_shadow/'
            os.makedirs( bakeDir )
            bpy.ops.image.new(name=collection.name, width=512, height=512)
            image = bpy.data.images[collection.name]
            for mat in bpy.data.materials:
                if "Cap" in mat.name:
                    mat.node_tree.nodes["Principled BSDF"].inputs[0].default_value = (1, 1, 1, 1)
                mat.use_nodes = True
                nodes = mat.node_tree.nodes
                node = nodes.new('ShaderNodeTexImage')
                node.image = image
                node.location = (100,100)
                node.select = True
                nodes.active = node
            for frame in range(1,end):
                scene.frame_set( frame )
                for obj in collection.all_objects:
                    bpy.context.view_layer.update()
                    if obj.type == 'MESH':
                        obj.select_set( True )
                        bpy.context.view_layer.objects.active = obj
                        bpy.ops.object.bake(type=bpy.context.scene.cycles.bake_type)
                image.filepath_raw = bakeDir + collection.name + '_shadow_' + str( frame ) + '.png'
                image.file_format = 'PNG'
                image.save()
            for mat in bpy.data.materials:
                if "Cap" in mat.name:
                    mat.node_tree.nodes["Principled BSDF"].inputs[0].default_value = ( 0.016, 0.016, 0.016, 1)
        
        




bake_map('roughness')
bake_map('normal')
bake_map('diffuse')
bake_plane()
bake_geos()
bake_emissive()

bpy.ops.wm.save_as_mainfile(filepath=output_dir+'demo.blend')

bpy.ops.wm.quit_blender()
