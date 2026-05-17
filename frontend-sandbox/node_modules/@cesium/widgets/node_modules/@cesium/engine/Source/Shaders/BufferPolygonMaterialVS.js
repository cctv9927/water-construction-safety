//This file is automatically rebuilt by the Cesium build process.
export default "in vec3 positionHigh;\n\
in vec3 positionLow;\n\
in vec4 pickColor;\n\
in vec2 showAndColor;\n\
\n\
out vec4 v_pickColor;\n\
out vec4 v_color;\n\
\n\
void main()\n\
{\n\
    float show = showAndColor.x;\n\
    vec4 color = czm_decodeRGB8(showAndColor.y);\n\
\n\
    ///////////////////////////////////////////////////////////////////////////\n\
\n\
    vec4 p = czm_translateRelativeToEye(positionHigh, positionLow);\n\
    vec4 positionEC = czm_modelViewRelativeToEye * p;\n\
\n\
    ///////////////////////////////////////////////////////////////////////////\n\
\n\
    gl_Position = czm_projection * positionEC;\n\
    czm_vertexLogDepth();\n\
\n\
    v_pickColor = pickColor / 255.0;\n\
\n\
    v_color = color;\n\
    v_color.a *= show;\n\
\n\
    gl_Position *= show;\n\
}\n\
";
