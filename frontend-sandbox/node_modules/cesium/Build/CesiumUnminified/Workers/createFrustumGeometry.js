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
  FrustumGeometry_default
} from "./chunk-3VDDRF2E.js";
import "./chunk-I3A6DXYZ.js";
import "./chunk-URUCCIPS.js";
import "./chunk-WC57YYBN.js";
import "./chunk-ZAPOS52G.js";
import "./chunk-QSDY4NS7.js";
import "./chunk-4MTRQFJP.js";
import "./chunk-WUBKZFF6.js";
import "./chunk-QXNQQYPV.js";
import "./chunk-77RL3MBD.js";
import "./chunk-TA777BGS.js";
import "./chunk-3TKLDHV3.js";
import "./chunk-ND3NTTOF.js";
import "./chunk-QO2CGXMP.js";
import "./chunk-DYT5NR6P.js";
import "./chunk-CZ23Y3RM.js";
import {
  defined_default
} from "./chunk-DH26SNAB.js";

// packages/engine/Source/Workers/createFrustumGeometry.js
function createFrustumGeometry(frustumGeometry, offset) {
  if (defined_default(offset)) {
    frustumGeometry = FrustumGeometry_default.unpack(frustumGeometry, offset);
  }
  return FrustumGeometry_default.createGeometry(frustumGeometry);
}
var createFrustumGeometry_default = createFrustumGeometry;
export {
  createFrustumGeometry_default as default
};
