import com.datastax.spark.connector._
import java.io.{ByteArrayOutputStream, ByteArrayInputStream}
import java.util.zip.{GZIPOutputStream, GZIPInputStream}

case class ObjdumpServiceName(service_name: String, sha256: String)
case class ObjdumpLabel(sha256: String, source_tags: String)
case class ObjdumpServiceNameAndLabel(sha256: String, service_name: String, source_tags: String)
case class ObjdumpSha256(sha256: String, service_name: String, results: Array[Byte])
case class ObjdumpJoin(sha256: String, service_name: String, results: String, source_tags: String)

def unzip(x: Array[Byte]) : String = {
    val inputStream = new GZIPInputStream(new ByteArrayInputStream(x));
    return scala.io.Source.fromInputStream(inputStream).mkString;
}

val objdump_service_name_rdd = sc.cassandraTable[ObjdumpServiceName](KEYSPACE, SERVICE_NAME_TABLE)
                             .where("service_name=?", "objdump")
                             .keyBy(x => (x.sha256));
val objdump_label_rdd = sc.cassandraTable[ObjdumpLabel](KEYSPACE, OBJECTS_TABLE)
                      .keyBy(x => (x.sha256));
val objdump_service_name_and_label_rdd = objdump_service_name_rdd.join(objdump_label_rdd)
                                       .map(x =>(new ObjdumpServiceNameAndLabel(x._1, x._2._1.service_name, x._2._2.source_tags)))
                                       .keyBy(x => (x.sha256, x.service_name));

val objdump_sha256_rdd = sc.cassandraTable[ObjdumpSha256](KEYSPACE, SHA256_TABLE)
                       .where("service_name=?", "objdump")
                       .keyBy(x => (x.sha256, x.service_name));
val objdump_join = objdump_service_name_and_label_rdd.join(objdump_sha256_rdd)
                 .map(x => (new ObjdumpJoin(x._1._1, x._1._2, unzip(x._2._2.results), x._2._1.source_tags)))
                 .distinct();

objdump_join.toDF().write.format("parquet").save("objdump.df");

