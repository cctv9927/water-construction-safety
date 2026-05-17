//This file is automatically rebuilt by the Cesium build process.
export default "in vec3 positionHigh;\n\
in vec3 positionLow;\n\
in vec3 prevPositionHigh;\n\
in vec3 prevPositionLow;\n\
in vec3 nextPositionHigh;\n\
in vec3 nextPositionLow;\n\
in vec4 pickColor;\n\
in vec4 showColorWidthAndTexCoord;\n\
\n\
out vec4 v_pickColor;\n\
out vec4 v_color;\n\
out vec2  v_st;\n\
out float v_width;\n\
out float v_polylineAngle;\n\
\n\
void main()\n\
{\n\
    float show = showColorWidthAndTexCoord.x;\n\
    vec4 color = czm_decodeRGB8(showColorWidthAndTexCoord.y);\n\
    float width = showColorWidthAndTexCoord.z;\n\
    float texCoord = showColorWidthAndTexCoord.w;\n\
\n\
    ///////////////////////////////////////////////////////////////////////////\n\
\n\
    bool usePrevious = texCoord == 1.0;\n\
    float expandDir = gl_VertexID % 2 == 1 ? 1.0 : -1.0;\n\
    float polylineAngle;\n\
\n\
    vec4 positionEC = czm_translateRelativeToEye(positionHigh, positionLow);\n\
    vec4 prevPositionEC = czm_translateRelativeToEye(prevPositionHigh, prevPositionLow);\n\
    vec4 nextPositionEC = czm_translateRelativeToEye(nextPositionHigh, nextPositionLow);\n\
\n\
    vec4 positionWC = getPolylineWindowCoordinates(positionEC, prevPositionEC, nextPositionEC, expandDir, width, usePrevious, polylineAngle);\n\
\n\
    ///////////////////////////////////////////////////////////////////////////\n\
\n\
    gl_Position = czm_viewportOrthographic * positionWC * show;\n\
\n\
    v_pickColor = pickColor / 255.0;\n\
\n\
    v_color = color;\n\
    v_color.a *= show;\n\
\n\
    v_st.s = texCoord;\n\
    v_st.t = czm_writeNonPerspective(clamp(expandDir, 0.0, 1.0), gl_Position.w);\n\
\n\
    v_width = width;\n\
    v_polylineAngle = polylineAngle;\n\
}\n\
";
