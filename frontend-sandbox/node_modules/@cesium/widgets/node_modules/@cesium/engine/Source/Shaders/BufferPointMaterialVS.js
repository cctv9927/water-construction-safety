//This file is automatically rebuilt by the Cesium build process.
export default "in vec3 positionHigh;\n\
in vec3 positionLow;\n\
in vec4 pickColor;\n\
in vec3 showPixelSizeAndColor;\n\
in vec2 outlineWidthAndOutlineColor;\n\
\n\
out vec4 v_pickColor;\n\
out vec4 v_color;\n\
out vec4 v_outlineColor;\n\
out float v_innerRadiusFrac;\n\
\n\
void main()\n\
{\n\
    // Unpack attributes.\n\
    float show = showPixelSizeAndColor.x;\n\
    float pixelSize = showPixelSizeAndColor.y;\n\
    vec4 color = czm_decodeRGB8(showPixelSizeAndColor.z);\n\
    float outlineWidth = outlineWidthAndOutlineColor.x;\n\
    vec4 outlineColor = czm_decodeRGB8(outlineWidthAndOutlineColor.y);\n\
\n\
    ///////////////////////////////////////////////////////////////////////////\n\
\n\
    float innerRadius = 0.5 * pixelSize * czm_pixelRatio;\n\
    float outerRadius = (0.5 * pixelSize + outlineWidth) * czm_pixelRatio;\n\
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
    v_outlineColor = outlineColor;\n\
    v_outlineColor.a *= show;\n\
\n\
    v_innerRadiusFrac = innerRadius / outerRadius;\n\
\n\
    gl_PointSize = 2.0 * outerRadius * show;\n\
    gl_Position *= show;\n\
}\n\
";
