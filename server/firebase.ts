/**
 * Firebase Admin SDK - Integração com as 4 instâncias do Nexus
 * Gerencia conexões com Nexus Genesis, Nexus-in, Nexus-HUB e Fundo Nexus
 */

import admin from "firebase-admin";
import * as fs from "fs";
import * as path from "path";

interface FirebaseInstance {
  app: admin.app.App;
  db: admin.database.Database;
  projectId: string;
  name: string;
}

interface ServiceAccountKey {
  type: string;
  project_id: string;
  private_key_id: string;
  private_key: string;
  client_email: string;
  client_id: string;
  auth_uri: string;
  token_uri: string;
  auth_provider_x509_cert_url: string;
  client_x509_cert_url: string;
  universe_domain: string;
}

const instances: Map<string, FirebaseInstance> = new Map();

/**
 * Inicializa uma instância do Firebase Admin SDK
 */
function initializeFirebaseInstance(
  name: string,
  keyPath: string
): FirebaseInstance | null {
  try {
    const serviceAccount = JSON.parse(
      fs.readFileSync(keyPath, "utf-8")
    ) as ServiceAccountKey;

    const app = admin.initializeApp(
      {
        credential: admin.credential.cert(serviceAccount as admin.ServiceAccount),
        databaseURL: `https://${serviceAccount.project_id}.firebaseio.com`,
      },
      name
    );

    const db = admin.database(app);

    console.log(`✅ Firebase inicializado para ${name}`);

    return {
      app,
      db,
      projectId: serviceAccount.project_id,
      name,
    };
  } catch (error) {
    console.warn(`⚠️ Erro ao inicializar Firebase para ${name}:`, error);
    return null;
  }
}

/**
 * Inicializa todas as instâncias do Nexus
 */
export function initializeAllFirebaseInstances(): void {
  const serverDir = path.join(process.cwd(), "server");

  // Nexus Genesis (instância central)
  try {
    const genesisPath = path.join(serverDir, "nexus_genesis_key.json");
    if (fs.existsSync(genesisPath)) {
      const instance = initializeFirebaseInstance("nexus_genesis", genesisPath);
      if (instance) instances.set("nexus_genesis", instance);
    }
  } catch (error) {
    console.warn("⚠️ Nexus Genesis não disponível:", error);
  }

  // Nexus-in
  try {
    const nexusInPath = path.join(
      serverDir,
      "API_Key chave privada Nexus-in studio-82398827-13646-firebase-adminsdk-fbsvc-15d0b960f7.json"
    );
    if (fs.existsSync(nexusInPath)) {
      const instance = initializeFirebaseInstance("nexus_in", nexusInPath);
      if (instance) instances.set("nexus_in", instance);
    }
  } catch (error) {
    console.warn("⚠️ Nexus-in não disponível:", error);
  }

  // Nexus-HUB
  try {
    const nexusHubPath = path.join(
      serverDir,
      "API_Key chave privada Nexus-HUB studio-204494591-85967-firebase-adminsdk-fbsvc-ec42290128.json"
    );
    if (fs.existsSync(nexusHubPath)) {
      const instance = initializeFirebaseInstance("nexus_hub", nexusHubPath);
      if (instance) instances.set("nexus_hub", instance);
    }
  } catch (error) {
    console.warn("⚠️ Nexus-HUB não disponível:", error);
  }

  // Fundo Nexus
  try {
    const fundoPath = path.join(
      serverDir,
      "API_Key chave privada Fundo Nexus studio-6829168551-a7f49-firebase-adminsdk-fbsvc-65f85ca5ae.json"
    );
    if (fs.existsSync(fundoPath)) {
      const instance = initializeFirebaseInstance("fundo_nexus", fundoPath);
      if (instance) instances.set("fundo_nexus", instance);
    }
  } catch (error) {
    console.warn("⚠️ Fundo Nexus não disponível:", error);
  }

  console.log(`\n🔷 ${instances.size} instâncias Firebase inicializadas`);
}

/**
 * Obtém uma instância do Firebase
 */
export function getFirebaseInstance(name: string): FirebaseInstance | undefined {
  return instances.get(name);
}

/**
 * Obtém todas as instâncias
 */
export function getAllFirebaseInstances(): Map<string, FirebaseInstance> {
  return instances;
}

/**
 * Obtém o banco de dados de uma instância
 */
export function getDatabase(name: string): admin.database.Database | undefined {
  return instances.get(name)?.db;
}

/**
 * Verifica a saúde de uma instância
 */
export async function checkInstanceHealth(
  name: string
): Promise<{ healthy: boolean; error?: string }> {
  try {
    const instance = instances.get(name);
    if (!instance) {
      return { healthy: false, error: "Instância não encontrada" };
    }

    const ref = instance.db.ref(".info/connected");
    const snapshot = await ref.once("value");
    const connected = snapshot.val();

    return { healthy: connected === true };
  } catch (error) {
    return {
      healthy: false,
      error: error instanceof Error ? error.message : "Erro desconhecido",
    };
  }
}

/**
 * Verifica a saúde de todas as instâncias
 */
export async function checkAllInstancesHealth(): Promise<
  Record<string, { healthy: boolean; error?: string }>
> {
  const health: Record<string, { healthy: boolean; error?: string }> = {};

  const entries = Array.from(instances.entries());
  for (const [name] of entries) {
    health[name] = await checkInstanceHealth(name);
  }

  return health;
}

/**
 * Lê dados de uma instância
 */
export async function readData(
  instanceName: string,
  path: string
): Promise<any> {
  try {
    const instance = instances.get(instanceName);
    if (!instance) {
      throw new Error(`Instância ${instanceName} não encontrada`);
    }

    const ref = instance.db.ref(path);
    const snapshot = await ref.once("value");
    return snapshot.val();
  } catch (error) {
    console.error(`Erro ao ler dados de ${instanceName}:`, error);
    throw error;
  }
}

/**
 * Escreve dados em uma instância
 */
export async function writeData(
  instanceName: string,
  path: string,
  data: any
): Promise<void> {
  try {
    const instance = instances.get(instanceName);
    if (!instance) {
      throw new Error(`Instância ${instanceName} não encontrada`);
    }

    const ref = instance.db.ref(path);
    await ref.set(data);
  } catch (error) {
    console.error(`Erro ao escrever dados em ${instanceName}:`, error);
    throw error;
  }
}

/**
 * Escuta mudanças em tempo real
 */
export function onDataChange(
  instanceName: string,
  path: string,
  callback: (data: any) => void
): () => void {
  try {
    const instance = instances.get(instanceName);
    if (!instance) {
      throw new Error(`Instância ${instanceName} não encontrada`);
    }

    const ref = instance.db.ref(path);
    ref.on("value", (snapshot: admin.database.DataSnapshot) => {
      callback(snapshot.val());
    });

    // Retorna função para remover o listener
    return () => ref.off("value");
  } catch (error) {
    console.error(`Erro ao escutar dados de ${instanceName}:`, error);
    throw error;
  }
}
