/**
 * @license
 * Cesium - https://github.com/CesiumGS/cesium
 * Version 1.141.0
 *
 * Copyright 2011-2022 Cesium Contributors
 *
 * Licensed under the Apache License, Version 2.0 (the "License");
 * you may not use this file except in compliance with the License.
 * You may obtain a copy of the License at
 *
 * http://www.apache.org/licenses/LICENSE-2.0
 *
 * Unless required by applicable law or agreed to in writing, software
 * distributed under the License is distributed on an "AS IS" BASIS,
 * WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
 * See the License for the specific language governing permissions and
 * limitations under the License.
 *
 * Columbus View (Pat. Pend.)
 *
 * Portions licensed separately.
 * See https://github.com/CesiumGS/cesium/blob/main/LICENSE.md for full licensing details.
 */

import {
  EllipseOutlineGeometry_default
} from "./chunk-EZARA5FJ.js";
import "./chunk-3XY3MVPG.js";
import "./chunk-6SDGQI27.js";
import "./chunk-LH5SF3XV.js";
import "./chunk-WC57YYBN.js";
import "./chunk-ZAPOS52G.js";
import "./chunk-QSDY4NS7.js";
import "./chunk-4MTRQFJP.js";
import "./chunk-WUBKZFF6.js";
import "./chunk-QXNQQYPV.js";
import "./chunk-77RL3MBD.js";
import "./chunk-TA777BGS.js";
import "./chunk-3TKLDHV3.js";
import {
  Ellipsoid_default
} from "./chunk-ND3NTTOF.js";
import {
  Cartesian3_default
} from "./chunk-QO2CGXMP.js";
import "./chunk-DYT5NR6P.js";
import "./chunk-CZ23Y3RM.js";
import {
  defined_default
} from "./chunk-DH26SNAB.js";

// packages/engine/Source/Workers/createEllipseOutlineGeometry.js
function createEllipseOutlineGeometry(ellipseGeometry, offset) {
  if (defined_default(offset)) {
    ellipseGeometry = EllipseOutlineGeometry_default.unpack(ellipseGeometry, offset);
  }
  ellipseGeometry._center = Cartesian3_default.clone(ellipseGeometry._center);
  ellipseGeometry._ellipsoid = Ellipsoid_default.clone(ellipseGeometry._ellipsoid);
  return EllipseOutlineGeometry_default.createGeometry(ellipseGeometry);
}
var createEllipseOutlineGeometry_default = createEllipseOutlineGeometry;
export {
  createEllipseOutlineGeometry_default as default
};
